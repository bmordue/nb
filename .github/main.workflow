workflow "Build container" {
  on = "push"
  resolves = ["GitHub Action for Docker-1"]
}

action "GitHub Action for Docker" {
  uses = "actions/docker/cli@76ff57a6c3d817840574a98950b0c7bc4e8a13a8"
  args = "build -t bmordue/nb -f src/Dockerfile ./src"
}

action "Docker Tag" {
  uses = "actions/docker/tag@76ff57a6c3d817840574a98950b0c7bc4e8a13a8"
  needs = ["GitHub Action for Docker"]
}

action "Docker Registry" {
  uses = "actions/docker/login@76ff57a6c3d817840574a98950b0c7bc4e8a13a8"
  needs = ["Docker Tag"]
  secrets = ["DOCKER_USERNAME", "DOCKER_PASSWORD"]
}

action "GitHub Action for Docker-1" {
  uses = "actions/docker/cli@76ff57a6c3d817840574a98950b0c7bc4e8a13a8"
  needs = ["Docker Registry"]
  args = "push"
}
