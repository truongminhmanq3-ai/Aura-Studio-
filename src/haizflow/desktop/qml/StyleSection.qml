import QtQuick
import QtQuick.Layouts
import "."

// A titled group of related style controls with a hairline under the title.
ColumnLayout {
    id: root

    property string title: ""
    default property alias content: body.data

    Layout.fillWidth: true
    spacing: Theme.space8

    Text {
        Layout.fillWidth: true
        visible: root.title.length > 0
        text: root.title
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: TypeScale.label
        font.weight: Font.DemiBold
        textFormat: Text.PlainText
    }

    Rectangle {
        Layout.fillWidth: true
        visible: root.title.length > 0
        implicitHeight: 1
        color: Theme.divider
    }

    ColumnLayout {
        id: body
        Layout.fillWidth: true
        spacing: Theme.space12
    }
}
