pragma ComponentBehavior: Bound
// qmllint disable missing-property
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Rectangle {
    id: root
    required property var credential
    property bool locked: false
    signal removeRequested(string id, string label)
    implicitHeight: 60
    color: Theme.surface
    radius: Theme.radiusSmall
    border.color: Theme.divider
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space16
        anchors.rightMargin: Theme.space12
        spacing: Theme.space12
        Text {
            Layout.fillWidth: true
            text: root.credential.label
            textFormat: Text.PlainText
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: TypeScale.body
            elide: Text.ElideRight
        }
        Text {
            visible: root.credential.active
            text: qsTr("Mặc định")
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: TypeScale.label
        }
        StudioButton {
            visible: !root.credential.active
            text: qsTr("Sử dụng")
            enabled: !root.locked
            onClicked: {
                AppController.selectGeminiApiKey(root.credential.id);
            }
        }
        StudioButton {
            text: qsTr("Xóa")
            enabled: !root.locked
            onClicked: root.removeRequested(root.credential.id, root.credential.label)
        }
    }
}
