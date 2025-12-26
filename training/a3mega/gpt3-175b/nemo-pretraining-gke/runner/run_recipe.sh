#!/bin/bash
# run_recipe.sh: Automates the functional validation of an AI Hypercomputer recipe.

# --- Configuration ---
# Fail fast on any error
set -e
set -o pipefail

# --- Argument Parsing ---
# The script expects the path to the recipe YAML file as the first argument.
RECIPE_YAML_PATH=$1
if [ -z "$RECIPE_YAML_PATH" ]; then
  echo "Error: Recipe YAML file path is not provided."
  echo "Usage: $0 <path-to-recipe.yaml>"
  exit 1
fi

echo "=== Using recipe configuration file: ${RECIPE_YAML_PATH} ==="

# --- Read Recipe Configuration ---
# This script assumes it runs from the root of the git repository.
# All paths in the recipe YAML should be relative to the repository root.
RECIPE_NAME=$(yq e '.recipe_name' "$RECIPE_YAML_PATH")
RECIPE_ROOT=$(yq e '.recipe_root' "$RECIPE_YAML_PATH")
HELM_CHART_PATH=$(yq e '.helm_chart_path' "$RECIPE_YAML_PATH")

# GKE and GCS Configuration
PROJECT_ID=$(yq e '.gcp.project_id' "$RECIPE_YAML_PATH")
CLUSTER_NAME=$(yq e '.gcp.cluster_name' "$RECIPE_YAML_PATH")
CLUSTER_REGION=$(yq e '.gcp.cluster_region' "$RECIPE_YAML_PATH")
GCS_BUCKET=$(yq e '.gcp.gcs_bucket' "$RECIPE_YAML_PATH")

# Workload Configuration
QUEUE_NAME=$(yq e '.workload.queue_name' "$RECIPE_YAML_PATH")
WORKLOAD_IMAGE=$(yq e '.workload.image' "$RECIPE_YAML_PATH")
WORKLOAD_LAUNCHER=$(yq e '.workload.launcher_path' "$RECIPE_YAML_PATH")
WORKLOAD_CONFIG=$(yq e '.workload.config_path' "$RECIPE_YAML_PATH")

# Validation Configuration
VALIDATION_TIMEOUT=$(yq e '.validation.timeout' "$RECIPE_YAML_PATH")

# --- Dynamic Values ---
# Generate a unique and idempotent Helm release name for this specific workflow run.
# Argo Workflows provides ARGO_WF_NAME as a unique identifier for the workflow.
if [ -n "$ARGO_WF_NAME" ]; then
  HELM_RELEASE_NAME="${RECIPE_NAME}-${ARGO_WF_NAME}"
else
  # Fallback for local execution
  HELM_RELEASE_NAME="${RECIPE_NAME}-$(date +%s)"
fi
# Helm release names have a length limit, so we truncate if necessary.
HELM_RELEASE_NAME=$(echo "$HELM_RELEASE_NAME" | cut -c 1-53)

echo "=== Configuration Summary ==="
echo "Recipe Name: ${RECIPE_NAME}"
echo "Helm Release Name: ${HELM_RELEASE_NAME}"
echo "Project ID: ${PROJECT_ID}"
echo "Cluster: ${CLUSTER_NAME} in ${CLUSTER_REGION}"
echo "GCS Bucket: ${GCS_BUCKET}"
echo "Queue: ${QUEUE_NAME}"
echo "Workload Image: ${WORKLOAD_IMAGE}"
echo "Helm Chart: ${HELM_CHART_PATH}"
echo "Validation Timeout: ${VALIDATION_TIMEOUT}s"
echo "============================="

# --- Cleanup ---
# Ensure the Helm release is uninstalled when the script exits,
# whether it succeeds or fails. This makes the validation idempotent.
cleanup() {
  echo "--- Performing cleanup: uninstalling Helm release ${HELM_RELEASE_NAME} ---"
  # Go back to the repo root to ensure helm can find the chart for uninstall if needed, though uninstall by name should be sufficient.
  cd /src
  helm uninstall "${HELM_RELEASE_NAME}" --wait || echo "Helm release ${HELM_RELEASE_NAME} not found or uninstall failed."
  echo "--- Cleanup complete ---"
}
trap cleanup EXIT

# --- Execution ---
echo "--- Step 1: Authenticating to GKE cluster ---"
gcloud config set project "${PROJECT_ID}"
gcloud container clusters get-credentials "${CLUSTER_NAME}" --region "${CLUSTER_REGION}"
echo "--- Authentication successful ---"

echo "--- Step 2: Submitting job with Helm ---"
# Navigate to the recipe directory to ensure relative paths in values.yaml are resolved correctly.
cd "${RECIPE_ROOT}"

helm install "${HELM_RELEASE_NAME}" "/src/${HELM_CHART_PATH}" \
  -f values.yaml \
  --set-file "workload_launcher=/src/${WORKLOAD_LAUNCHER}" \
  --set-file "workload_config=/src/${WORKLOAD_CONFIG}" \
  --set "queue=${QUEUE_NAME}" \
  --set "volumes.gcsMounts[0].bucketName=${GCS_BUCKET}" \
  --set "workload.image=${WORKLOAD_IMAGE}"

echo "--- Helm install command submitted ---"

# --- Validation ---
echo "--- Step 3: Validating JobSet and Pod creation ---"
echo "Waiting up to ${VALIDATION_TIMEOUT} seconds for resources to be created..."

JOBSET_NAME=""
POD_COUNT=0
SECONDS=0
while [ $SECONDS -lt "$VALIDATION_TIMEOUT" ]; do
  # Check for the JobSet
  # The JobSet name is derived from the Helm release name.
  JOBSET_NAME=$(kubectl get jobset -l "app.kubernetes.io/instance=${HELM_RELEASE_NAME}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
  if [ -n "$JOBSET_NAME" ]; then
    echo "Validation PASSED: JobSet '${JOBSET_NAME}' found."

    # Check for associated Pods
    POD_COUNT=$(kubectl get pods -l "app.kubernetes.io/instance=${HELM_RELEASE_NAME}" --no-headers 2>/dev/null | wc -l)
    if [ "$POD_COUNT" -gt 0 ]; then
      echo "Validation PASSED: Found ${POD_COUNT} pods associated with the Helm release."
      echo "--- Functional validation successful! ---"
      exit 0
    fi
  fi

  sleep 5
  SECONDS=$((SECONDS + 5))
  echo "Still waiting... (${SECONDS}s / ${VALIDATION_TIMEOUT}s)"
done

echo "--- Validation FAILED: Timed out after ${VALIDATION_TIMEOUT} seconds. ---"
if [ -z "$JOBSET_NAME" ]; then
    echo "Error: JobSet for Helm release '${HELM_RELEASE_NAME}' was not created."
else
    echo "Error: JobSet '${JOBSET_NAME}' was created, but no pods were found."
fi

# Explicitly exit with an error code for clarity
exit 1
