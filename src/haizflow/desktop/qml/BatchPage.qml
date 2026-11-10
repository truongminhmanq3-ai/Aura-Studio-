pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Item {
    id: root

    signal openVideoDetail
    signal requestBatchSettings
    signal requestUrlImport
    signal requestDownloadProjectImport

    property bool dropActive: false
    readonly property bool compactHeight: height < 740
    property var settingOverrides: []
    function refreshOverrides() { settingOverrides = AppController.batchSettingOverrides(); }
    readonly property var statusLabels: ({
        "pending": qsTr("Đang chờ"), "processing": qsTr("Đang xử lý"), "awaiting_review": qsTr("Cần duyệt"),
        "paused": qsTr("Đã tạm dừng"), "done": qsTr("Hoàn tất"), "failed": qsTr("Lỗi hoặc đã hủy")
    })
    // [{value, label}] built from live counts so the picker only offers what exists.
    function channelModel() {
        const options = AppController.batchChannelOptions;
        return options.map(function(option) {
            const name = option.value === "" ? qsTr("Tất cả kênh")
                : option.value === "__none__" ? qsTr("Không rõ kênh") : option.label;
            return { "value": option.value, "label": qsTr("%1 (%2)").arg(name).arg(option.count) };
        });
    }
    function statusModel() {
        const counts = AppController.batchStatusCounts;
        const result = [{ "value": "", "label": qsTr("Mọi trạng thái (%1)").arg(AppController.batchCount) }];
        ["pending", "processing", "awaiting_review", "paused", "done", "failed"].forEach(function(key) {
            if (counts[key] > 0)
                result.push({ "value": key, "label": qsTr("%1 (%2)").arg(root.statusLabels[key]).arg(counts[key]) });
        });
        return result;
    }
    function applyFilter() {
        AppController.setBatchFilter(channelFilter.currentValue === undefined ? "" : channelFilter.currentValue,
                                     statusFilter.currentValue === undefined ? "" : statusFilter.currentValue);
    }
    Component.onCompleted: refreshOverrides()
    Connections {
        target: AppController
        function onBatchChanged() { root.refreshOverrides(); }
    }

    function importDrop(drop) {
        root.dropActive = false;
        if (!drop.urls || drop.urls.length === 0)
            return;
        const paths = [];
        for (let index = 0; index < drop.urls.length; ++index)
            paths.push(String(drop.urls[index]));
        AppController.importBatchVideos(paths);
    }

    opacity: visible ? 1 : 0
    transform: Translate {
        y: root.visible ? 0 : 8
        Behavior on y {
            NumberAnimation {
                duration: Theme.motionStandard
                easing.type: Easing.OutCubic
            }
        }
    }
    Behavior on opacity {
        NumberAnimation {
            duration: Theme.motionStandard
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: UiMetrics.pageMargin
        spacing: root.compactHeight ? Theme.space12 : Theme.space16

        PageHeader {
            Layout.fillWidth: true
            title: AppController.projectName || qsTr("Dự án hàng loạt")

            Text {
                text: qsTr("%1 %2").arg(AppController.batchCount).arg(qsTr("video"))
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: TypeScale.label
                textFormat: Text.PlainText
            }

            ProjectHeaderActions {
                projectFolderEnabled: AppController.hasOpenProject
                deleteEnabled: AppController.hasOpenProject
                onProjectFolderRequested: AppController.openProjectFolder()
                onDeleteRequested: AppController.deleteCurrentBatch()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.minimumHeight: 52
            Layout.preferredHeight: 52
            Layout.maximumHeight: 52
            spacing: Theme.space12

            Rectangle {
                id: importCard

                Layout.preferredWidth: 440
                Layout.minimumWidth: 260
                Layout.maximumWidth: 520
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radiusSmall
                color: root.dropActive ? Theme.interactiveMuted : Theme.surfaceElevated
                border.width: root.dropActive ? 2 : 1
                border.color: root.dropActive ? Theme.focus : Theme.outline

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space12
                    anchors.rightMargin: Theme.space12
                    spacing: Theme.space8

                    Text {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        text: AppController.mediaImportBusy ? qsTr("Adding %1 / %2…").arg(AppController.mediaImportCompleted).arg(AppController.mediaImportTotal) : root.dropActive ? qsTr("Thả để thêm video") : qsTr("Thêm vào hàng đợi")
                        color: Theme.text
                        font.pixelSize: Theme.caption
                        font.weight: Font.DemiBold
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                    }

                    MediaSourceImportButton {
                        Layout.preferredWidth: 132
                        variant: AppController.batchCount === 0 ? "primary" : "secondary"
                        onFileRequested: AppController.browseBatchVideos()
                        onLinkRequested: root.requestUrlImport()
                        onDownloadProjectRequested: root.requestDownloadProjectImport()
                    }
                }

                DropArea {
                    anchors.fill: parent
                    keys: ["text/uri-list"]
                    onEntered: function (drag) {
                        if (drag.hasUrls) {
                            root.dropActive = true;
                            drag.accept();
                        }
                    }
                    onExited: root.dropActive = false
                    onDropped: function (drop) {
                        root.importDrop(drop);
                    }
                }
            }

            Item {
                Layout.fillWidth: true
            }

            StudioButton {
                text: qsTr("Cài đặt hàng loạt")
                iconGlyph: "\uE713"
                variant: "secondary"
                enabled: !AppController.isBatchRunning
                onClicked: root.requestBatchSettings()
            }

            StudioButton {
                visible: !AppController.isBatchRunning
                text: qsTr("Xử lý")
                iconGlyph: "\uE768"
                variant: "primary"
                enabled: AppController.batchCount > 0 && !AppController.videoExportBusy
                onClicked: AppController.requestBatchProcessing()
            }

            StudioButton {
                visible: !AppController.isBatchRunning && AppController.batchPausedCount > 0
                text: qsTr("Tiếp tục")
                iconGlyph: "\uE768"
                variant: "secondary"
                enabled: !AppController.videoExportBusy
                onClicked: AppController.resumeBatch()
            }

            StudioButton {
                visible: AppController.isBatchRunning
                text: AppController.isBatchPausing ? qsTr("Đang tạm dừng") : qsTr("Tạm dừng xử lý")
                iconGlyph: "\uE71A"
                variant: "danger"
                enabled: !AppController.isBatchPausing
                onClicked: AppController.stopBatch()
            }
        }

        RowLayout {
            id: filterBar
            objectName: "batchFilterBar"
            Layout.fillWidth: true
            visible: AppController.batchCount > 0
            spacing: Theme.space12

            AppComboBox {
                id: channelFilter
                objectName: "batchChannelFilter"
                Layout.preferredWidth: 230
                visible: AppController.batchChannelOptions.length > 1
                model: root.channelModel()
                textRole: "label"
                valueRole: "value"
                Accessible.name: qsTr("Lọc theo kênh")
                onActivated: root.applyFilter()
            }

            AppComboBox {
                id: statusFilter
                objectName: "batchStatusFilter"
                Layout.preferredWidth: 220
                model: root.statusModel()
                textRole: "label"
                valueRole: "value"
                Accessible.name: qsTr("Lọc theo trạng thái")
                onActivated: root.applyFilter()
            }

            Connections {
                target: AppController
                function onBatchChanged() {
                    // Progress ticks also arrive here: rebuild the pickers only when their content changed,
                    // so an open drop-down is not closed under the user's hand.
                    const channel = AppController.batchFilterChannel;
                    const status = AppController.batchFilterStatus;
                    const channels = root.channelModel();
                    const statuses = root.statusModel();
                    if (JSON.stringify(channels) !== JSON.stringify(channelFilter.model))
                        channelFilter.model = channels;
                    if (JSON.stringify(statuses) !== JSON.stringify(statusFilter.model))
                        statusFilter.model = statuses;
                    channelFilter.currentIndex = Math.max(0, channelFilter.indexOfValue(channel));
                    statusFilter.currentIndex = Math.max(0, statusFilter.indexOfValue(status));
                    if (status !== "" && statusFilter.indexOfValue(status) < 0)
                        AppController.setBatchFilter(channel, "");   // that status group is empty now
                }
            }

            Text {
                objectName: "batchFilterCount"
                visible: AppController.batchFilterActive
                text: qsTr("Đang hiện %1 / %2 video").arg(AppController.batchVisibleCount).arg(AppController.batchCount)
                color: Theme.textMuted
                font.pixelSize: Theme.caption
                textFormat: Text.PlainText
            }

            StudioButton {
                visible: AppController.batchFilterActive
                text: qsTr("Bỏ lọc")
                variant: "ghost"
                onClicked: {
                    channelFilter.currentIndex = 0;
                    statusFilter.currentIndex = 0;
                    root.applyFilter();
                }
            }

            Item { Layout.fillWidth: true }

            StudioButton {
                objectName: "batchProcessFiltered"
                visible: AppController.batchFilterActive && !AppController.isBatchRunning
                text: qsTr("Xử lý %1 video đang lọc").arg(AppController.batchVisibleCount)
                variant: "secondary"
                enabled: AppController.batchVisibleCount > 0 && !AppController.videoExportBusy
                onClicked: AppController.requestBatchProcessingFiltered()
            }

            StudioButton {
                objectName: "batchRetryFailed"
                visible: AppController.batchFailedCount > 0 && !AppController.isBatchRunning
                text: qsTr("Thử lại %1 video lỗi").arg(AppController.batchFailedCount)
                variant: "secondary"
                enabled: !AppController.videoExportBusy
                onClicked: AppController.requestBatchRetryFailed()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space12

            Text {
                Layout.fillWidth: true
                text: qsTr("Hàng đợi xử lý")
                color: Theme.text
                font.pixelSize: Theme.h2
                font.weight: Font.DemiBold
                textFormat: Text.PlainText
            }

            Text {
                visible: root.settingOverrides.length > 0
                text: qsTr("%1 video dùng cài đặt riêng").arg(root.settingOverrides.length)
                color: Theme.textMuted
                font.pixelSize: Theme.caption
                textFormat: Text.PlainText
            }

            Rectangle {
                visible: AppController.isBatchRunning
                Layout.preferredWidth: queueStateLabel.implicitWidth + Theme.space20
                Layout.preferredHeight: 28
                radius: Theme.radiusSmall
                color: Theme.warningMuted

                Text {
                    id: queueStateLabel
                    anchors.centerIn: parent
                    text: AppController.isBatchPausing ? qsTr("Đang tạm dừng") : qsTr("Đang xử lý")
                    color: Theme.warning
                    font.pixelSize: Theme.label
                    font.weight: Font.DemiBold
                    textFormat: Text.PlainText
                }
            }

            Text {
                visible: AppController.batchCount > 0
                text: qsTr("%1 %2").arg(AppController.batchCount).arg(qsTr("mục"))
                color: Theme.textMuted
                font.pixelSize: Theme.caption
                textFormat: Text.PlainText
            }
        }

        Rectangle {
            id: queuePanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: queueList.cellHeight + Theme.space12
            radius: Theme.radius
            color: Theme.surface
            border.width: root.dropActive ? 2 : 1
            border.color: root.dropActive ? Theme.focus : Theme.outline

            DropArea {
                anchors.fill: parent
                keys: ["text/uri-list"]
                onEntered: function (drag) {
                    if (drag.hasUrls) {
                        root.dropActive = true;
                        drag.accept();
                    }
                }
                onExited: root.dropActive = false
                onDropped: function (drop) { root.importDrop(drop); }
            }

            GridView {
                id: queueList

                // Keep batch cards at the same compact scale as project cards.
                readonly property int columnCount: Math.max(1, Math.floor((width + Theme.space16) / (200 + Theme.space16)))
                readonly property real cellContentWidth: Math.floor(width / columnCount)
                readonly property real cardWidth: Math.min(220, Math.max(1, cellContentWidth - Theme.space16))
                readonly property real cardHeight: Math.round(cardWidth * 0.56 + 64)

                anchors.fill: parent
                anchors.margins: AppController.batchCount > 0 ? Theme.space12 : 0
                clip: true
                model: AppController.filteredBatchVideoModel
                reuseItems: true
                cellWidth: cellContentWidth
                cellHeight: cardHeight + Theme.space16

                delegate: BatchVideoCard {
                    required property string videoId
                    customSettings: root.settingOverrides.some(item => item.videoId === videoId)
                    width: queueList.cardWidth
                    height: queueList.cardHeight
                    onActivated: {
                        AppController.selectFilteredBatchVideo(index);
                        root.openVideoDetail();
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }
            }

            Column {
                anchors.centerIn: parent
                width: Math.min(420, parent.width - 40)
                spacing: Theme.space8
                visible: AppController.batchCount === 0

                Text {
                    width: parent.width
                    text: qsTr("Hàng đợi đang trống")
                    color: Theme.text
                    font.pixelSize: Theme.h3
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    textFormat: Text.PlainText
                }

                Text {
                    width: parent.width
                    text: qsTr("Nhập nguồn hoặc kéo video vào đây để thêm vào hàng đợi")
                    color: Theme.textMuted
                    font.pixelSize: Theme.caption
                    horizontalAlignment: Text.AlignHCenter
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
            }
        }

        Rectangle {
            id: batchProgressPanel
            visible: AppController.batchCount > 0

            Layout.fillWidth: true
            Layout.minimumHeight: 52
            Layout.preferredHeight: 52
            Layout.maximumHeight: 52
            radius: Theme.radiusSmall
            color: Theme.surfaceElevated
            border.width: 1
            border.color: Theme.outline

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space12
                anchors.rightMargin: Theme.space12
                spacing: Theme.space12

                InfoRow {
                    Layout.preferredWidth: 78
                    label: qsTr("Video")
                    value: String(AppController.batchCount)
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 28
                    color: Theme.divider
                }

                InfoRow {
                    Layout.preferredWidth: 112
                    label: qsTr("Hoàn tất")
                    value: qsTr("%1 / %2").arg(AppController.batchCompletedCount).arg(AppController.batchCount)
                }

                ColumnLayout {
                    visible: root.width >= 1180
                    Layout.preferredWidth: visible ? 150 : 0
                    spacing: 3

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Ngôn ngữ đích")
                        color: Theme.textMuted
                        font.pixelSize: Theme.label
                        textFormat: Text.PlainText
                    }

                    Text {
                        Layout.fillWidth: true
                        text: AppController.batchTargetLanguageLabel
                        color: Theme.text
                        font.pixelSize: Theme.body
                        font.weight: Font.DemiBold
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space4

                    RowLayout {
                        Layout.fillWidth: true

                        Text {
                            Layout.fillWidth: true
                            text: AppController.isBatchRunning ? qsTr("Đang xử lý hàng đợi") : qsTr("Tiến độ tổng")
                            color: Theme.textMuted
                            font.pixelSize: Theme.caption
                            textFormat: Text.PlainText
                        }

                        Text {
                            text: qsTr("%1%").arg(AppController.batchProgress)
                            color: Theme.text
                            font.pixelSize: Theme.h3
                            font.weight: Font.DemiBold
                            textFormat: Text.PlainText
                        }
                    }

                    AppProgressBar {
                        Layout.fillWidth: true
                        value: AppController.batchProgress
                        active: AppController.isBatchRunning
                    }
                }
            }
        }
    }
}
