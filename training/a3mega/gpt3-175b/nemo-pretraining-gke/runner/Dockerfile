# Dockerfile for the Argo Workflow runner
# This image contains gcloud, kubectl, helm, and yq
# to execute the recipe validation script.

FROM google/cloud-sdk:alpine

# Install kubectl
RUN gcloud components install kubectl

# Install helm
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 && \
    chmod 700 get_helm.sh && \
    ./get_helm.sh

# Install yq
RUN wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 && \
    chmod a+x /usr/local/bin/yq

# Copy the script to run the recipe
COPY run_recipe.sh /usr/local/bin/run_recipe.sh
RUN chmod +x /usr/local/bin/run_recipe.sh

ENTRYPOINT ["/usr/local/bin/run_recipe.sh"]
