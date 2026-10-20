import QtQuick
import QtQuick.Layouts
import "."

Rectangle {
    id: root
    property string activityState: "ready"
    property string message: ""
    property real progress: -1
    property bool expanded: false
    property bool showDetails: true
    signal detailsRequested()

    // Keep the status strip's geometry stable. Model warm-up used to remove
    // this item when it finished, making every workspace visibly grow after
    // a few seconds even though the window DPI and font sizes had not changed.
    implicitHeight: UiMetrics.activityTrayHeight
    visible: true
    radius: 15
    color: "transparent"
    border.width: 1.5
    border.color: "#FFFFFF"

    Rectangle {
        anchors.fill: parent
        radius: 15
        color: "transparent"
        border.width: 1
        border.color: "#18000000"
    }

    gradient: Gradient {
        GradientStop { position: 0.0; color: "#30FFFFFF" }
        GradientStop { position: 0.5; color: "#12FFFFFF" }
        GradientStop { position: 1.0; color: "#26FFFFFF" }
    }

    function stateLabel(state) {
        if (state === "failed") return qsTr("Có lỗi");
        if (state === "processing") return qsTr("Đang xử lý");
        if (state === "paused") return qsTr("Đã tạm dừng");
        if (state === "queued") return qsTr("Đang chờ");
        return qsTr("Sẵn sàng");
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 8
        visible: true

        Rectangle {
            width: 6
            height: 6
            radius: 3
            color: root.activityState === "failed" ? Theme.danger
                : root.activityState === "processing" ? Theme.interactive
                : root.activityState === "paused" || root.activityState === "queued"
                    ? Theme.warning : Theme.success
        }

        Text {
            objectName: "activityStatusLabel"
            text: root.stateLabel(root.activityState)
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: TypeScale.metadata
            font.weight: Font.Medium
            textFormat: Text.PlainText
        }
        Rectangle {
            visible: root.message.length > 0
            Layout.preferredWidth: 1
            Layout.preferredHeight: 12
            color: Theme.divider
        }
        Text {
            Layout.fillWidth: true
            text: root.message
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: TypeScale.label
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        AppProgressBar {
            visible: root.activityState === "processing" || root.progress >= 0
            Layout.preferredWidth: 140
            value: Math.max(0, root.progress * 100)
            indeterminate: root.progress < 0
            active: root.activityState === "processing"
        }
        Text {
            visible: root.progress >= 0
            Layout.preferredWidth: 38
            text: Math.round(root.progress * 100) + "%"
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: TypeScale.metadata
            horizontalAlignment: Text.AlignRight
            textFormat: Text.PlainText
        }
        StudioButton {
            visible: root.showDetails && root.activityState !== "ready"
            variant: "ghost"
            text: qsTr("Chi tiết")
            onClicked: root.detailsRequested()
        }
    }
}
