pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

FloatingToolDialog {
    id: root

    signal subtitleLayoutEdited(int fontSize, int positionX, int positionY, int boxWidth, int boxHeight)
    signal autoAlignmentEdited(bool enabled)
    signal subtitleAppearanceEdited(var patch)
    property var appearance: AppController.subtitleAppearance
    property var draftAppearance: ({})
    readonly property var sampleRenderer: AppController.subtitleSampleOverlayRenderer
    readonly property string longSampleText: qsTr("Một buổi sáng, chúng tôi cùng nhau đi qua con phố nhỏ để khám phá những câu chuyện thú vị. Kéo rộng khung để hiển thị nhiều từ hơn trên mỗi dòng, hoặc kéo cao khung để xem phụ đề trên nhiều dòng.")
    property bool coverEnabled: false
    property bool autoAlignToCover: false
    property var coverLayout: ({})
    readonly property bool layoutLocked: coverEnabled && autoAlignToCover
    property string safeZonePreset: "all"
    readonly property var previewMedia: AppController.reviewPreviewMedia || ({})
    readonly property int sourceWidth: Number(previewMedia.videoWidth || 1920)
    readonly property int sourceHeight: Number(previewMedia.videoHeight || 1080)

    property int draftFontSize: 60
    property int draftPositionX: 51
    property int draftPositionY: 96
    property int draftBoxWidth: 72
    property int draftBoxHeight: 6

    function clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value));
    }

    function previewSprite(frame) {
        if (!frame || !frame.normal)
            return ({});
        const lines = frame.karaokeLines || [];
        const totalCs = lines.reduce(function(total, line) { return total + line.durationCs; }, 0);
        const elapsedCs = totalCs * 0.45;
        return Object.assign({}, frame, {
            progress: 0.45,
            karaokeLines: lines.map(function(line) {
                return Object.assign({}, line, {
                    progress: line.durationCs > 0
                        ? root.clamp((elapsedCs - line.startCs) / line.durationCs, 0, 1)
                        : Number(elapsedCs >= line.startCs)
                });
            })
        });
    }

    function openWithLayout(fontSize, positionX, positionY, boxWidth, boxHeight) {
        draftFontSize = clamp(Number(fontSize), 10, 240);
        draftPositionX = clamp(Number(positionX), 0, 100);
        draftPositionY = clamp(Number(positionY), 0, 100);
        draftBoxWidth = clamp(Number(boxWidth), 20, 100);
        draftBoxHeight = clamp(Number(boxHeight), 1, 100);
        open();
    }

    function refreshSample() {
        if (!opened || !sampleRenderer)
            return;
        const style = draftAppearance;
        const layout = {
            outputWidth: sourceWidth,
            outputHeight: sourceHeight,
            layoutWidth: sourceWidth * transform.boxWidthPercent / 100,
            layoutHeight: sourceHeight * transform.boxHeightPercent / 100,
            fontSize: transform.fontSize,
            positionXPercent: transform.positionXPercent,
            positionYPercent: transform.positionYPercent,
            fontFamily: style.font_family || "Bangers",
            textColor: style.text_color || "#FFFFFF",
            karaokeColor: style.karaoke_color || "#FFEF00",
            outlineColor: style.outline_color || "#000000",
            outline: Number(style.outline ?? 2),
            shadow: Number(style.shadow ?? 2),
            bold: Boolean(style.bold),
            italic: Boolean(style.italic),
            uppercase: Boolean(style.uppercase),
            letterSpacing: Number(style.letter_spacing ?? 0),
            alignment: style.alignment || "center"
        };
        sampleRenderer.configure(JSON.stringify([
            {
                start: 0,
                end: 10,
                text: longSampleText
            }
        ]), JSON.stringify(layout), true, true);
        sampleRenderer.seek(0);
    }
    function scheduleSample() {
        if (opened && !sampleRefresh.running)
            sampleRefresh.start();
    }
    function editAppearance(patch) {
        draftAppearance = Object.assign({}, draftAppearance, patch);
        if (patch.font_size !== undefined)
            draftFontSize = Number(patch.font_size);
        subtitleAppearanceEdited(patch);
    }
    onOpened: {
        draftAppearance = Object.assign({}, appearance);
        sampleRefresh.restart();
    }
    onClosed: {
        sampleRefresh.stop();
        if (sampleRenderer)
            sampleRenderer.clear();
    }
    onDraftAppearanceChanged: scheduleSample()
    onDraftFontSizeChanged: scheduleSample()
    onDraftPositionXChanged: scheduleSample()
    onDraftPositionYChanged: scheduleSample()
    onDraftBoxWidthChanged: scheduleSample()
    onDraftBoxHeightChanged: scheduleSample()
    onLayoutLockedChanged: scheduleSample()
    onCoverLayoutChanged: scheduleSample()
    Timer {
        id: sampleRefresh
        interval: 180
        onTriggered: root.refreshSample()
    }

    expandedWidth: 1100
    expandedHeight: 760
    toolTitle: qsTr("Chỉnh phụ đề")
    toolSubtitle: layoutLocked 
        ? qsTr("Chế độ căn ô che: Màu sắc & viền tùy chỉnh tự do · Vị trí khóa theo ô che") 
        : qsTr("Chế độ tự do: Kéo hai bên để đổi số từ · Kéo góc để đổi cỡ & vị trí")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space16
        spacing: Theme.space12

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.coverEnabled
            spacing: 2

            StudioCheckBox {
                objectName: "subtitleAutoCoverCheck"
                Layout.fillWidth: true
                text: qsTr("Tự động căn vị trí và cỡ chữ vào ô che tiếng Trung")
                checked: root.autoAlignToCover
                onToggled: root.autoAlignmentEdited(checked)
            }

            Text {
                text: root.autoAlignToCover 
                    ? qsTr("💡 Vị trí và cỡ chữ được tự động khóa vừa khít ô che. Bạn vẫn có thể thoải mái chọn màu sắc, viền và kiểu chữ ở cột bên phải.")
                    : qsTr("💡 Chế độ tự do: Bạn có thể kéo góc hoặc kéo cạnh khung chữ trên màn hình để đặt vị trí tùy thích.")
                font.pixelSize: TypeScale.caption
                color: root.autoAlignToCover ? Theme.interactive : Theme.textMuted
                Layout.leftMargin: 28
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.space16
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 240
                Layout.minimumHeight: 220
                radius: Theme.radiusSmall
                color: Theme.video
                border.width: 1
                border.color: Theme.outline
                clip: true

                Image {
                    id: previewImage
                    anchors.fill: parent
                    anchors.margins: 1
                    source: AppController.videoThumbnailSource
                    sourceSize.width: 1280
                    sourceSize.height: 720
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                }

                SafeZoneOverlay {
                    id: safeZone
                    videoRect: Qt.rect(previewImage.x + (previewImage.width - previewImage.paintedWidth) / 2, previewImage.y + (previewImage.height - previewImage.paintedHeight) / 2, previewImage.paintedWidth, previewImage.paintedHeight)
                    preset: root.safeZonePreset
                    z: 1
                }

                SubtitleTransformOverlay {
                    id: transform
                    z: 2
                    objectName: "autoSubtitleTransformOverlay"
                    anchors.fill: parent
                    videoRect: Qt.rect(previewImage.x + (previewImage.width - previewImage.paintedWidth) / 2, previewImage.y + (previewImage.height - previewImage.paintedHeight) / 2, previewImage.paintedWidth, previewImage.paintedHeight)
                    sampleText: AppController.subtitleSampleText(root.longSampleText, fontSize, boxWidthPercent, boxHeightPercent, root.sourceWidth, root.sourceHeight, root.draftAppearance)
                    sprite: root.previewSprite(root.sampleRenderer ? root.sampleRenderer.frame : ({}))
                    sampleFontFamily: root.draftAppearance.font_family || sampleFont.name
                    sampleFontScale: AppController.subtitlePreviewFontScale
                    sampleTextColor: root.draftAppearance.text_color || "#FFFFFF"
                    sampleOutlineColor: root.draftAppearance.outline_color || "#000000"
                    sampleBold: Boolean(root.draftAppearance.bold)
                    sampleItalic: Boolean(root.draftAppearance.italic)
                    fontSize: root.layoutLocked ? Number(root.coverLayout.fontSize || root.draftFontSize) : root.draftFontSize
                    positionXPercent: root.layoutLocked ? Number(root.coverLayout.positionXPercent !== undefined ? root.coverLayout.positionXPercent : 50) : root.draftPositionX
                    positionYPercent: root.layoutLocked ? Number(root.coverLayout.positionYPercent !== undefined ? root.coverLayout.positionYPercent : 80) : root.draftPositionY
                    boxWidthPercent: root.layoutLocked ? Number(root.coverLayout.boxWidthPercent || 72) : root.draftBoxWidth
                    boxHeightPercent: root.layoutLocked ? Number(root.coverLayout.boxHeightPercent || 12) : root.draftBoxHeight
                    referenceWidthPixels: root.sourceWidth
                    referenceHeightPixels: root.sourceHeight
                    interactive: !root.layoutLocked
                    editing: !root.layoutLocked
                    onLayoutPreviewChanged: function (fontSize, positionX, positionY, boxWidth, boxHeight) {
                        root.draftFontSize = fontSize;
                        root.draftPositionX = positionX;
                        root.draftPositionY = positionY;
                        root.draftBoxWidth = boxWidth;
                        root.draftBoxHeight = boxHeight;
                    }
                    onLayoutCommitted: function (fontSize, positionX, positionY, boxWidth, boxHeight) {
                        root.draftFontSize = fontSize;
                        root.draftPositionX = positionX;
                        root.draftPositionY = positionY;
                        root.draftBoxWidth = boxWidth;
                        root.draftBoxHeight = boxHeight;
                        root.subtitleLayoutEdited(fontSize, positionX, positionY, root.draftBoxWidth, root.draftBoxHeight);
                    }
                }
            }

            Flickable {
                objectName: "subtitleAppearanceScroll"
                Layout.preferredWidth: 290
                Layout.minimumWidth: 260
                Layout.maximumWidth: 310
                Layout.fillHeight: true
                contentHeight: appearanceControls.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.VerticalFlick
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }
                SubtitleAppearanceControls {
                    id: appearanceControls
                    width: parent.width - Theme.space12
                    style: Object.assign({}, root.draftAppearance, {
                        font_size: root.draftFontSize
                    })
                    enabled: true
                    onChangeRequested: function (patch) {
                        root.editAppearance(patch);
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space8

            Text {
                text: qsTr("Lưới an toàn:")
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: TypeScale.caption
                font.weight: Font.DemiBold
            }

            StudioButton {
                text: qsTr("Tắt")
                variant: root.safeZonePreset === "none" ? "primary" : "secondary"
                onClicked: root.safeZonePreset = "none"
            }

            StudioButton {
                text: qsTr("Chung")
                variant: root.safeZonePreset === "all" ? "primary" : "secondary"
                onClicked: root.safeZonePreset = "all"
            }

            StudioButton {
                text: qsTr("TikTok")
                variant: root.safeZonePreset === "tiktok" ? "primary" : "secondary"
                onClicked: root.safeZonePreset = "tiktok"
            }

            StudioButton {
                text: qsTr("Reels")
                variant: root.safeZonePreset === "reels" ? "primary" : "secondary"
                onClicked: root.safeZonePreset = "reels"
            }

            StudioButton {
                text: qsTr("Shorts")
                variant: root.safeZonePreset === "shorts" ? "primary" : "secondary"
                onClicked: root.safeZonePreset = "shorts"
            }

            Item {
                Layout.fillWidth: true
            }

            StudioButton {
                text: qsTr("Căn vị trí vàng (Y=70%)")
                iconGlyph: "\uE73E"
                variant: "secondary"
                enabled: !root.layoutLocked
                onClicked: {
                    root.draftPositionX = 50;
                    root.draftPositionY = 70;
                    root.subtitleLayoutEdited(root.draftFontSize, 50, 70, root.draftBoxWidth, root.draftBoxHeight);
                }
            }

            StudioButton {
                text: qsTr("Căn giữa (50%)")
                variant: "secondary"
                enabled: !root.layoutLocked
                onClicked: {
                    root.draftPositionX = 50;
                    root.draftPositionY = 50;
                    root.subtitleLayoutEdited(root.draftFontSize, 50, 50, root.draftBoxWidth, root.draftBoxHeight);
                }
            }

            StudioButton {
                text: qsTr("Đặt lại")
                variant: "secondary"
                enabled: !root.layoutLocked
                onClicked: {
                    root.draftPositionX = 51;
                    root.draftPositionY = 96;
                    root.subtitleLayoutEdited(root.draftFontSize, 51, 96, root.draftBoxWidth, root.draftBoxHeight);
                }
            }
        }
    }

    FontLoader {
        id: sampleFont
        source: "../../assets/fonts/Bangers-Regular.ttf"
    }
}
