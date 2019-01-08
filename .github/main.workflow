workflow "Build and push docker image" {
  on = "push"
  resolves = ["GitHub Action for Docker-1"]
}

action "Build and tag" {
  uses = "actions/docker/cli@76ff57a6c3d817840574a98950b0c7bc4e8a13a8"
  args = "build -t bmordue/nb -f src/Dockerfile ./src"
}

action "Log in to Docker Hub" {
  uses = "actions/docker/login@76ff57a6c3d817840574a98950b0c7bc4e8a13a8"
  needs = ["Build and tag"]
  secrets = ["DOCKER_USERNAME", "DOCKER_PASSWORD"]
}

action "Push to Docker Hub" {
  uses = "actions/docker/cli@76ff57a6c3d817840574a98950b0c7bc4e8a13a8"
  needs = ["Docker in to Docker Hub"]
  args = "push"
}
