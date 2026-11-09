pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

AppDialog {
    id: root
    objectName: "chineseTextDialog"

    property bool blurEnabled: true
    property var items: []
    readonly property int selectedCount: items.filter(function(item) { return item.enabled; }).length

    function reload() {
        const overview = AppController.chineseTextOverview();
        root.blurEnabled = Boolean(overview.enabled);
        root.items = overview.items || [];
    }

    subtitle: qsTr("Chữ Trung Quốc tự nhận diện trên video. Bỏ chọn vùng bạn muốn giữ nguyên.")
    preferredWidth: 620
    maximumWidth: 720
    preferredHeight: 560
    onAboutToShow: root.reload()

    StudioCheckBox {
        objectName: "chineseTextBlurToggle"
        Layout.fillWidth: true
        text: qsTr("Làm mờ chữ Trung Quốc khi xuất video")
        checked: root.blurEnabled
        onToggled: {
            AppController.setChineseTextBlurEnabled(checked);
            root.reload();
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space8
        Text {
            Layout.fillWidth: true
            text: root.items.length > 0
                ? qsTr("Đã chọn %1 / %2 vùng").arg(root.selectedCount).arg(root.items.length)
                : ""
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.caption
            textFormat: Text.PlainText
        }
        StudioButton {
            text: qsTr("Chọn tất cả")
            variant: "ghost"
            enabled: root.items.length > 0 && root.blurEnabled
            onClicked: { AppController.setChineseTextAllEnabled(true); root.reload(); }
        }
        StudioButton {
            text: qsTr("Bỏ chọn tất cả")
            variant: "ghost"
            enabled: root.items.length > 0 && root.blurEnabled
            onClicked: { AppController.setChineseTextAllEnabled(false); root.reload(); }
        }
    }

    Text {
        Layout.fillWidth: true
        visible: root.items.length === 0
        text: qsTr("Chưa có dữ liệu. Hãy bấm “Xử lý lại” để app quét chữ Trung Quốc trên video này.")
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: TypeScale.control
        wrapMode: Text.WordWrap
        textFormat: Text.PlainText
    }

    ListView {
        id: list
        objectName: "chineseTextList"
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 200
        visible: root.items.length > 0
        enabled: root.blurEnabled
        opacity: root.blurEnabled ? 1 : 0.5
        clip: true
        spacing: Theme.space8
        model: root.items
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        delegate: Rectangle {
            id: row
            required property var modelData
            width: ListView.view.width - Theme.space12
            height: 64
            radius: Theme.radiusTiny
            color: Theme.surfaceMuted
            border.width: 1
            border.color: Theme.outline

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.space8
                spacing: Theme.space12

                StudioCheckBox {
                    objectName: "chineseTextTrackCheck"
                    checked: row.modelData.enabled
                    onToggled: {
                        AppController.setChineseTextTrackEnabled(row.modelData.id, checked);
                        root.reload();
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 132
                    Layout.preferredHeight: 44
                    radius: 6
                    color: Theme.surfaceStrong
                    clip: true
                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        fillMode: Image.PreserveAspectFit
                        source: row.modelData.thumbnailUrl || ""
                        asynchronous: true
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        Layout.fillWidth: true
                        text: row.modelData.text
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: TypeScale.control
                        elide: Text.ElideRight
                        textFormat: Text.PlainText
                    }
                    Text {
                        Layout.fillWidth: true
                        text: ({ "subtitle": qsTr("Phụ đề"), "overlay": qsTr("Chữ chồng lên hình"),
                                 "scene": qsTr("Chữ trong cảnh") })[row.modelData.kind]
                            + " · " + row.modelData.startSeconds.toFixed(1) + "s – "
                            + row.modelData.endSeconds.toFixed(1) + "s"
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.caption
                        elide: Text.ElideRight
                        textFormat: Text.PlainText
                    }
                }
            }
        }
    }

    footerActions: [
        StudioButton {
            text: qsTr("Xong")
            variant: "primary"
            onClicked: root.accept()
        }
    ]
}
