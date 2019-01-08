VERSION=v0.0.1
TAG=$VERSION-$(git rev-parse --short HEAD)
git tag -a $TAG -m "Release $TAG by script" && git push origin $TAG
