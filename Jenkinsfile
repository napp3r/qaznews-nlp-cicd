pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    // A local Jenkins cannot receive GitHub webhooks, so the repository is polled every minute.
    triggers {
        pollSCM('* * * * *')
    }

    environment {
        IMAGE_NAME = 'qaznews-nlp'
        NAMESPACE = 'qaznews-test'
        KIND_CLUSTER = 'qaznews'
    }

    stages {
        stage('Prepare') {
            steps {
                script {
                    env.IMAGE_TAG = sh(script: 'git rev-parse --short=8 HEAD', returnStdout: true).trim()
                    env.TEST_IMAGE = "${env.IMAGE_NAME}:test-${env.IMAGE_TAG}"
                    env.TRAIN_IMAGE = "${env.IMAGE_NAME}:train-${env.IMAGE_TAG}"
                    env.IMAGE = "${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                    env.IS_MAIN = (env.GIT_BRANCH == 'origin/main').toString()
                }
                sh 'docker version --format "Docker server {{.Server.Version}}"'
                echo "Branch ${env.GIT_BRANCH}, image ${env.IMAGE}"
            }
        }

        stage('Lint') {
            steps {
                sh 'docker build --target test -t "$TEST_IMAGE" .'
                sh 'docker run --rm "$TEST_IMAGE" sh -c "ruff check . && ruff format --check ."'
            }
        }

        stage('Unit tests') {
            steps {
                sh '''
                    mkdir -p reports
                    docker run --name "unit-$BUILD_TAG" "$TEST_IMAGE" pytest --junitxml=/tmp/junit.xml
                '''
            }
            post {
                always {
                    sh '''
                        docker cp "unit-$BUILD_TAG:/tmp/junit.xml" reports/junit.xml || true
                        docker rm -f "unit-$BUILD_TAG" || true
                    '''
                    junit testResults: 'reports/junit.xml', allowEmptyResults: true
                }
            }
        }

        stage('Train and quality gate') {
            steps {
                sh 'docker build --target train --build-arg MODEL_VERSION="$IMAGE_TAG" -t "$TRAIN_IMAGE" .'
                sh '''
                    cid="$(docker create "$TRAIN_IMAGE")"
                    docker cp "$cid:/app/artifacts/metrics.json" reports/metrics.json
                    docker rm "$cid"
                    cat reports/metrics.json
                '''
                archiveArtifacts artifacts: 'reports/metrics.json', fingerprint: true
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    docker build --target runtime --build-arg MODEL_VERSION="$IMAGE_TAG" \
                        --provenance=false -t "$IMAGE" .
                    docker image inspect "$IMAGE" --format "Built {{.RepoTags}}, {{.Size}} bytes"
                '''
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    docker run -d --name "smoke-$BUILD_TAG" "$IMAGE"
                    docker exec "smoke-$BUILD_TAG" python -m qaznews.smoke
                '''
            }
            post {
                always {
                    sh 'docker rm -f "smoke-$BUILD_TAG" || true'
                }
            }
        }

        stage('Push to Docker Hub') {
            when {
                allOf {
                    environment name: 'IS_MAIN', value: 'true'
                    environment name: 'DOCKERHUB_ENABLED', value: 'true'
                }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                                  usernameVariable: 'HUB_USER',
                                                  passwordVariable: 'HUB_TOKEN')]) {
                    sh '''
                        export DOCKER_CONFIG="$WORKSPACE/.docker"
                        echo "$HUB_TOKEN" | docker login -u "$HUB_USER" --password-stdin
                        docker tag "$IMAGE" "$HUB_USER/$IMAGE_NAME:$IMAGE_TAG"
                        docker tag "$IMAGE" "$HUB_USER/$IMAGE_NAME:latest"
                        docker push "$HUB_USER/$IMAGE_NAME:$IMAGE_TAG"
                        docker push "$HUB_USER/$IMAGE_NAME:latest"
                        docker logout
                        docker rmi "$HUB_USER/$IMAGE_NAME:$IMAGE_TAG" "$HUB_USER/$IMAGE_NAME:latest"
                        rm -rf "$DOCKER_CONFIG"
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            when {
                environment name: 'IS_MAIN', value: 'true'
            }
            steps {
                sh '''
                    kind load docker-image "$IMAGE" --name "$KIND_CLUSTER"
                    kubectl apply -f k8s/namespace.yaml -f k8s/service.yaml
                    sed "s|IMAGE_PLACEHOLDER|$IMAGE|" k8s/deployment.yaml | kubectl apply -f -
                    if ! kubectl -n "$NAMESPACE" rollout status deployment/qaznews-api --timeout=180s; then
                        kubectl -n "$NAMESPACE" rollout undo deployment/qaznews-api
                        exit 1
                    fi
                    kubectl -n "$NAMESPACE" get pods -o wide
                '''
            }
        }

        stage('Verify deployment') {
            when {
                environment name: 'IS_MAIN', value: 'true'
            }
            steps {
                sh '''
                    kubectl -n "$NAMESPACE" run "smoke-$BUILD_NUMBER" --rm -i --restart=Never \
                        --image="$IMAGE" --image-pull-policy=IfNotPresent \
                        --command -- python -m qaznews.smoke --url http://qaznews-api:8000
                '''
            }
        }
    }

    post {
        always {
            // Only this build's helper tags: the runtime image stays available for rollback.
            sh 'docker rmi "$TEST_IMAGE" "$TRAIN_IMAGE" || true'
            sh 'if [ "$IS_MAIN" != "true" ]; then docker rmi "$IMAGE" || true; fi'
        }
        success {
            echo "Pipeline passed for ${env.IMAGE}"
        }
        failure {
            echo "Pipeline failed on branch ${env.GIT_BRANCH}: nothing was deployed by this build"
        }
    }
}
