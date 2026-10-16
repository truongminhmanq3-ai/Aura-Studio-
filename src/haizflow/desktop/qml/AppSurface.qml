import QtQuick
import QtQuick.Layouts
import "."

Rectangle {
    id: root

    property string tone: "default"
    property int padding: Theme.space16
    property int spacing: Theme.space12
    default property alias content: contentColumn.data

    color: "transparent"
    border.width: 1.5
    border.color: "#FFFFFF"
    radius: Theme.radius
    implicitHeight: contentColumn.implicitHeight + padding * 2

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: "transparent"
        border.width: 1
        border.color: "#1A000000"
    }

    gradient: Gradient {
        GradientStop {
            position: 0.0
            color: root.tone === "raised" ? "#45FFFFFF"
                : root.tone === "muted" ? "#28FFFFFF" : "#36FFFFFF"
        }
        GradientStop {
            position: 0.5
            color: "#14FFFFFF"
        }
        GradientStop {
            position: 1.0
            color: root.tone === "raised" ? "#36FFFFFF"
                : root.tone === "muted" ? "#1FFFFFFF" : "#28FFFFFF"
        }
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: root.padding
        spacing: root.spacing
    }
}
