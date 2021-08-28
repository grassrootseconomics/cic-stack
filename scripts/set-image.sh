#! /bin/bash

set -e

cd kubernetes/

kustomize edit set image registry.gitlab.com/grassrootseconomics/cic-internal-integration/cic-cache:$TAG

kustomize edit set image registry.gitlab.com/grassrootseconomics/cic-internal-integration/bloxberg-node:$TAG

kustomize edit set image registry.gitlab.com/grassrootseconomics/cic-internal-integration/contract-migration:$TAG

kustomize edit set image registry.gitlab.com/grassrootseconomics/cic-internal-integration/cic-eth:$TAG

kustomize edit set image registry.gitlab.com/grassrootseconomics/cic-internal-integration/cic-notify:$TAG

kustomize edit set image registry.gitlab.com/grassrootseconomics/cic-internal-integration/cic-meta:$TAG

kustomize edit set image registry.gitlab.com/grassrootseconomics/cic-internal-integration/cic-ussd:$TAG

echo "kustomize set image to ${TAG? no variable TAG set}"
