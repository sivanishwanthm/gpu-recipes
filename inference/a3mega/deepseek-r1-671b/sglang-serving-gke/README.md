# DeepSeek R1 671B Inference with SGLang on A3 Mega

This recipe deploys and benchmarks the DeepSeek R1 671B model on a multi-node A3 Mega GKE cluster using SGLang for distributed inference. By following these steps, you will have a serving endpoint for the model and performance benchmark results.

## Prerequisites

Before you begin, ensure you have the following:

*   A configured GKE cluster with an A3 Mega node pool. For setup instructions, see the [GKE environment setup guide](../../../../docs/configuring-environment-gke-a3-mega.md).
*   An Artifact Registry repository to store the Docker image.
*   A Google Cloud Storage (GCS) bucket in the same region as your GKE cluster.
*   A client workstation with the Google Cloud SDK, Helm, and kubectl installed.
*   A [Hugging Face account](https://huggingface.co/) and an access token with at least `Read` permissions to access the model.

## Deploy the Model

1.  To begin, open a new session in [Google Cloud Shell](https://console.cloud.google.com/?cloudshell=true).

2.  Set the environment variables to match your project configuration:
    ```bash
    export PROJECT_ID=<PROJECT_ID>
    export REGION=<REGION>
    export CLUSTER_REGION=<CLUSTER_REGION>
    export CLUSTER_NAME=<CLUSTER_NAME>
    export GCS_BUCKET=<GCS_BUCKET>
    export ARTIFACT_REGISTRY=<ARTIFACT_REGISTRY>
    export SGLANG_IMAGE=sglang
    export SGLANG_VERSION=v0.4.3.post2-cu125-srt
    ```
    These variables are now configured for your current session.

3.  Set the default Google Cloud project:
    ```bash
    gcloud config set project $PROJECT_ID
    ```
    Your active project is now set to the one specified.

4.  Clone the `gpu-recipes` repository and define the recipe's root directory:
    ```bash
    git clone https://github.com/ai-hypercomputer/gpu-recipes.git
    cd gpu-recipes
    export REPO_ROOT=`git rev-parse --show-toplevel`
    export RECIPE_ROOT=$REPO_ROOT/inference/a3mega/deepseek-r1-671b/sglang-serving-gke
    ```
    You are now in the repository's root directory with the `RECIPE_ROOT` variable set.

5.  Get the credentials for your GKE cluster:
    ```bash
    gcloud container clusters get-credentials $CLUSTER_NAME --region $CLUSTER_REGION
    ```
    Your `kubectl` context is now configured to communicate with your cluster.

6.  Use Cloud Build to build and push the container image to your Artifact Registry:
    ```bash
    cd $REPO_ROOT/src/docker/sglang
    gcloud builds submit --region=${REGION} \
        --config cloudbuild.yml \
        --substitutions _ARTIFACT_REGISTRY=$ARTIFACT_REGISTRY,_SGLANG_IMAGE=$SGLANG_IMAGE,_SGLANG_VERSION=$SGLANG_VERSION \
        --timeout "2h" \
        --machine-type=e2-highcpu-32 \
        --disk-size=1000 \
        --quiet \
        --async
    ```
    This command starts the build process and returns a build ID.

7.  Create a Kubernetes secret with your Hugging Face token to download the model checkpoints:
    ```bash
    export HF_TOKEN=<YOUR_HUGGINGFACE_TOKEN>
    kubectl create secret generic hf-secret \
    --from-literal=hf_api_token=${HF_TOKEN} \
    --dry-run=client -o yaml | kubectl apply -f -
    ```
    The secret `hf-secret` is now created in your cluster.

8.  Install the LeaderWorkerSet (LWS) API to manage the distributed workload:
    ```bash
    kubectl apply --server-side -f https://github.com/kubernetes-sigs/lws/releases/latest/download/manifests.yaml
    ```
    The LWS controller is now installed in the `lws-system` namespace.

9.  Verify that the LeaderWorkerSet controller is running:
    ```bash
    kubectl get pod -n lws-system
    ```
    The output shows the controller pod with a `Running` status.

10. Install the Helm chart to deploy the model serving application:
    ```bash
    cd $RECIPE_ROOT
    helm install -f values.yaml \
    --set job.image.repository=${ARTIFACT_REGISTRY}/${SGLANG_IMAGE} \
    --set clusterName=${CLUSTER_NAME} \
    --set job.image.tag=${SGLANG_VERSION} \
    --set volumes.gcsMounts[0].bucketName=${GCS_BUCKET} \
    $USER-serving-deepseek-r1-model \
    $REPO_ROOT/src/helm-charts/a3mega/sglang-inference
    ```
    The Helm chart is installed, and the model deployment begins.

11. View the deployment logs to monitor the server startup:
    ```bash
    kubectl logs -f service/$USER-serving-deepseek-r1-model-svc
    ```
    The logs will stream, and you will see a confirmation message when the server is ready.

12. Port-forward the service to your local machine to send requests:
    ```bash
    kubectl port-forward svc/$USER-serving-deepseek-r1-model-svc 30000:30000
    ```
    The service is now accessible on `localhost:30000`.

13. Send a chat completion request to the model:
    ```bash
    curl http://localhost:30000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model":"default",
      "messages":[
          {
            "role":"system",
            "content":"You are a helpful AI assistant"
          },
          {
            "role":"user",
            "content":"How many r are there in strawberry ?"
          }
      ],
      "temperature":0.6,
      "top_p":0.95,
      "max_tokens":2048
    }'
    ```
    The model returns a JSON response containing the answer.

14. Run the SGLang benchmarking tool to measure inference performance:
    ```bash
    kubectl exec -it service/$USER-serving-deepseek-r1-model-svc -- /bin/bash -c "python3 -m sglang.bench_serving --backend sglang --dataset-name random --random-range-ratio 1 --num-prompt 1100 --random-input 1000 --random-output 1000 --host 0.0.0.0 --port 30000 --output-file /gcs/benchmark_logs/sglang/ds_1000_1000_1100_output.jsonl"
    ```
    After the benchmark completes, the results are saved to the specified GCS bucket.

## Cleanup

When you are done with your GPU VM, follow these steps to clean up your resources.

1.  Uninstall the Helm chart:
    ```bash
    helm uninstall $USER-serving-deepseek-r1-model
    ```
    This command removes the resources created by the Helm deployment.

2.  Delete the Kubernetes secret:
    ```bash
    kubectl delete secret hf-secret
    ```
    This command permanently deletes the Hugging Face token secret from the cluster.

## What's Next

*   Explore other [inference recipes](/inference/).
*   Learn more about [SGLang](https://github.com/sgl-project/sglang).
*   Read the official documentation on [A3 Mega VMs](https://cloud.google.com/compute/docs/a3-vms).
