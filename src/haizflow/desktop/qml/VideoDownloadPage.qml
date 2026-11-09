import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Item {
    id: root

    required property var downloader

    Connections {
        target: root.downloader
        function onWorkspaceChanged() {
            videoLink.text = String(root.downloader.workspaceState.videoUrl || root.downloader.videoPreviewUrl || "");
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.space16

        ScrollView {
            id: videoScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            ColumnLayout {
                width: videoScroll.availableWidth
                spacing: Theme.space16

                AppSurface {
                    Layout.fillWidth: true
                    padding: Theme.space16

                    SectionHeader {
                        Layout.fillWidth: true
                        title: qsTr("Liên kết video")
                    }

                    AppTextField {
                        id: videoLink
                        Layout.fillWidth: true
                        placeholderText: qsTr("Dán liên kết video")
                        selectByMouse: true
                        accessibleName: qsTr("Liên kết video")
                        enabled: !root.downloader.videoPreviewBusy
                        text: String(root.downloader.workspaceState.videoUrl || root.downloader.videoPreviewUrl || "")
                        onTextEdited: {
                            root.downloader.clearVideoPreview();
                            root.downloader.saveWorkspaceState({videoUrl: text});
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        StudioButton {
                            text: qsTr("Kiểm tra")
                            variant: "secondary"
                            enabled: videoLink.text.trim().length > 0 && !root.downloader.videoPreviewBusy
                                && douyinAction.permitsRequest
                            onClicked: root.downloader.inspectVideo(videoLink.text.trim())
                        }
                        StudioButton {
                            visible: root.downloader.videoPreviewBusy
                            text: qsTr("Hủy")
                            variant: "danger"
                            onClicked: root.downloader.cancelVideoPreview()
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: root.downloader.videoPreviewStatus.length > 0
                            text: I18n.runtimeStatus(root.downloader.videoPreviewStatus)
                            color: root.downloader.videoPreviewReady ? Theme.success : Theme.textMuted
                            wrapMode: Text.WordWrap
                            textFormat: Text.PlainText
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                        visible: root.downloader.videoPreviewReady
                        radius: Theme.radiusSmall
                        color: Theme.surfaceElevated
                        border.width: 1
                        border.color: Theme.outline

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.space12
                            spacing: Theme.space12

                            Rectangle {
                                Layout.preferredWidth: 132
                                Layout.preferredHeight: 76
                                radius: Theme.radiusTiny
                                color: Theme.surfaceStrong
                                clip: true

                                Image {
                                    id: previewThumbnail
                                    anchors.fill: parent
                                    source: root.downloader.videoPreviewThumbnail
                                    sourceSize.width: 264
                                    sourceSize.height: 152
                                    asynchronous: true
                                    fillMode: Image.PreserveAspectCrop
                                    visible: status === Image.Ready
                                }
                                ThumbnailFallback {
                                    anchors.fill: parent
                                    visible: root.downloader.videoPreviewThumbnail.length === 0 || previewThumbnail.status === Image.Error
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Theme.space4
                                Text {
                                    Layout.fillWidth: true
                                    text: root.downloader.videoPreviewTitle
                                    color: Theme.text
                                    font.pixelSize: Theme.body
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                    textFormat: Text.PlainText
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: [root.downloader.videoPreviewPlatform, root.downloader.videoPreviewUploader, root.downloader.videoPreviewDuration].filter(function(value) { return value.length > 0 }).join(" | ")
                                    color: Theme.textMuted
                                    font.pixelSize: Theme.caption
                                    elide: Text.ElideRight
                                    textFormat: Text.PlainText
                                }
                            }
                        }
                    }

                    DownloadDestinationRow {

                        Layout.fillWidth: true
                        directory: root.downloader.videoOutputDirectory
                        managed: root.downloader.outputManaged
                        onChooseRequested: root.downloader.chooseVideoOutputDirectory()
                    }

                    DouyinSessionAction {
                        id: douyinAction
                        Layout.fillWidth: true
                        url: videoLink.text
                        visible: requiresSession
                        operationBusy: root.downloader.videoPreviewBusy || root.downloader.hasWork
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Item { Layout.fillWidth: true }
                        StudioButton {
                            text: qsTr("Tải video")
                            variant: "primary"
                            enabled: root.downloader.videoPreviewReady && root.downloader.videoOutputDirectory.length > 0
                                && douyinAction.permitsRequest
                            onClicked: root.downloader.downloadVideo(root.downloader.videoPreviewUrl)
                        }
                    }
                }

                AppSurface {
                    id: batchSurface
                    objectName: "linkBatchSurface"
                    Layout.fillWidth: true
                    padding: Theme.space16

                    property var parsed: ({ "count": 0, "duplicates": 0, "rejected": [], "truncated": false })
                    readonly property string firstLink: batchLinks.text.match(/https?:\/\/[^\s]+|v\.douyin\.com\/[^\s]+/i)
                        ? batchLinks.text.match(/https?:\/\/[^\s]+|v\.douyin\.com\/[^\s]+/i)[0] : ""

                    SectionHeader {
                        Layout.fillWidth: true
                        title: qsTr("Tải nhiều link cùng lúc")
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Dán cả đoạn chữ chứa nhiều link (mỗi link một dòng, hoặc nguyên câu chia sẻ từ Douyin). App tự tìm link, bỏ link trùng và tải lần lượt; link nào lỗi thì bỏ qua và tải tiếp.")
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.caption
                        wrapMode: Text.WordWrap
                        textFormat: Text.PlainText
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        enabled: !root.downloader.batchActive
                        AppTextArea {
                            id: batchLinks
                            objectName: "linkBatchInput"
                            placeholderText: qsTr("Dán các link video vào đây")
                            accessibleName: qsTr("Danh sách link video")
                            onTextChanged: batchSurface.parsed = root.downloader.previewLinkBatch(text)
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: batchLinks.text.trim().length > 0
                        text: batchSurface.parsed.count > 0
                            ? qsTr("Tìm thấy %1 link hợp lệ").arg(batchSurface.parsed.count)
                                + (batchSurface.parsed.duplicates > 0 ? qsTr(" · bỏ %1 link trùng").arg(batchSurface.parsed.duplicates) : "")
                                + (batchSurface.parsed.rejected.length > 0 ? qsTr(" · %1 link không hỗ trợ").arg(batchSurface.parsed.rejected.length) : "")
                                + (batchSurface.parsed.truncated ? qsTr(" · chỉ lấy 500 link đầu") : "")
                            : qsTr("Chưa thấy link video hợp lệ nào.")
                        color: batchSurface.parsed.count > 0 ? Theme.success : Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.caption
                        wrapMode: Text.WordWrap
                        textFormat: Text.PlainText
                    }

                    DouyinSessionAction {
                        id: batchDouyinAction
                        Layout.fillWidth: true
                        url: batchSurface.firstLink
                        visible: requiresSession
                        operationBusy: root.downloader.hasWork
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space8
                        Text {
                            Layout.fillWidth: true
                            text: root.downloader.batchSummary
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: TypeScale.control
                            font.weight: Font.Medium
                            wrapMode: Text.WordWrap
                            textFormat: Text.PlainText
                        }
                        StudioButton {
                            visible: root.downloader.batchActive
                            text: qsTr("Hủy")
                            variant: "danger"
                            onClicked: root.downloader.cancel()
                        }
                        StudioButton {
                            text: qsTr("Tải tất cả (%1)").arg(batchSurface.parsed.count)
                            variant: "primary"
                            enabled: batchSurface.parsed.count > 0 && !root.downloader.hasWork
                                && root.downloader.videoOutputDirectory.length > 0 && batchDouyinAction.permitsRequest
                            onClicked: root.downloader.downloadVideoBatch(batchLinks.text)
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.downloader.batchStoppedReason.length > 0 && !root.downloader.batchActive
                        text: root.downloader.batchStoppedReason === "Cancelled"
                            ? qsTr("Đã hủy. Các link chưa tải nằm trong danh sách bên dưới.")
                            : qsTr("Douyin đang yêu cầu phiên mới hoặc xác minh nên app đã dừng để không bị chặn thêm. Bấm “Tạo phiên Douyin” rồi dán lại danh sách bên dưới để tải tiếp.")
                        color: Theme.warning
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.caption
                        wrapMode: Text.WordWrap
                        textFormat: Text.PlainText
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: root.downloader.batchFailures.length > 0
                        spacing: Theme.space4
                        Repeater {
                            model: root.downloader.batchFailures
                            delegate: Text {
                                required property var modelData
                                Layout.fillWidth: true
                                text: modelData.url + " — " + I18n.runtimeStatus(modelData.reason)
                                color: Theme.danger
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.caption
                                elide: Text.ElideMiddle
                                textFormat: Text.PlainText
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.downloader.batchRetryText.length > 0 && !root.downloader.batchActive
                        spacing: Theme.space8
                        StudioButton {
                            text: qsTr("Đưa link chưa tải vào ô nhập")
                            variant: "secondary"
                            onClicked: batchLinks.text = root.downloader.batchRetryText
                        }
                        StudioButton {
                            text: qsTr("Xóa kết quả")
                            variant: "ghost"
                            onClicked: root.downloader.clearBatch()
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
