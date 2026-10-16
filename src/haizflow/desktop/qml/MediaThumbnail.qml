import QtQuick
import "."

Rectangle {
    id: root
    property url source: ""
    property string fallbackIcon: "video"

    radius: 18
    color: "transparent"
    border.width: 1
    border.color: "#18000000"
    clip: true

    Image {
        id: thumbnailImage
        anchors.fill: parent
        source: root.source
        sourceSize.width: Math.max(1, Math.round(width * 2))
        sourceSize.height: Math.max(1, Math.round(height * 2))
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        visible: status === Image.Ready
    }

    Image {
        anchors.fill: parent
        visible: root.source.toString().length === 0 || thumbnailImage.status === Image.Error
        source: Qt.resolvedUrl("../assets/branding/apple-card-art.png")
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
    }
}
