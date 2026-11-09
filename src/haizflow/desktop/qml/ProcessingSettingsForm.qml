import QtQuick
import QtQuick.Layouts
import "."

GridLayout {
    id: root

    property bool editable: true
    property bool cpuOnly: false
    property bool hasSource: false
    property bool showCloneAction: false
    property bool showMusicPlaybackSettings: true
    property real availableHeight: 0
    readonly property real voiceSpacing: root.speakerMode === "multiple"
        ? Math.max(Theme.space6, Math.min(Theme.space10, Theme.space6 + (availableHeight - 520) / 30))
        : Math.max(Theme.space8, Math.min(Theme.space20, Theme.space8 + (availableHeight - 500) / 18))
    readonly property real mediaSpacing: Math.max(6, Math.min(Theme.space14,
        6 + (availableHeight - 500) / 24))
    property string speechRecognitionModel: "groq-whisper"
    property string translationModel: "auto"
    property var speechRecognitionOptions: []
    property int speechRecognitionIndex: 0
    property string targetLanguage: "vi"
    property var targetLanguageOptions: []
    property string ttsProvider: "omnivoice"
    property var ttsProviderOptions: []
    property int ttsProviderIndex: 0
    property string ttsVoice: ""
    property var ttsVoiceOptions: []
    property var femaleVoiceOptions: []
    property var maleVoiceOptions: []
    property string femaleVoice: "Trúc Ly"
    property string maleVoice: "Hải Đăng"
    property string voicePreviewSource: ""
    property string voicePreviewState: "idle"
    property string speakerMode: "single"
    property bool removeOriginalSubtitles: true
    property string subtitleRemovalMode: "patch"
    property bool enableAudioSeparation: true
    property string backgroundMusicPath: ""
    property bool backgroundMusicLoop: true
    property bool audioDuckingEnabled: false
    property int audioDuckingReductionDb: -12
    property string watermarkText: ""
    property string watermarkKind: "text"
    property string watermarkImagePath: ""
    property string watermarkVideoPath: ""

    signal speechRecognitionEdited(string value)
    signal translationModelEdited(string value)
    signal targetLanguageEdited(string value)
    signal ttsProviderEdited(string value)
    signal ttsVoiceEdited(string value)
    signal femaleVoiceEdited(string value)
    signal maleVoiceEdited(string value)
    signal ttsVoicePreviewRequested(string value)
    signal cloneVoiceRequested()
    signal speakerModeEdited(string value)
    signal removeOriginalSubtitlesEdited(bool value)
    signal subtitleRemovalModeEdited(string value)
    signal subtitleLayoutRequested()
    signal audioSeparationEdited(bool value)
    signal audioMixRequested()
    signal backgroundMusicFileRequested()
    signal backgroundMusicLinkRequested()
    signal backgroundMusicClearRequested()
    signal backgroundMusicLoopEdited(bool value)
    signal audioDuckingEdited(bool value)
    signal audioDuckingReductionEdited(int value)
    signal watermarkKindEdited(string value)
    signal watermarkRequested()

    function multipleFallbackVoice() {
        if (root.ttsProvider === "elevenlabs") {
            for (let i = 0; i < root.ttsVoiceOptions.length; ++i) {
                const candidate = String(root.ttsVoiceOptions[i].voice || "");
                if (candidate.indexOf("elevenlabs:") === 0)
                    return candidate;
            }
        }
        return "omnivoice:female";
    }

    columns: width >= 650 ? 2 : 1
    columnSpacing: Theme.space20
    rowSpacing: Theme.space16

    Item {
        Layout.fillWidth: true
        Layout.fillHeight: root.columns === 2
        Layout.alignment: Qt.AlignTop
        implicitHeight: voiceColumn.implicitHeight

        ColumnLayout {
            id: voiceColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: Theme.space4
            anchors.rightMargin: Theme.space4
            spacing: root.voiceSpacing

            Text {
                text: qsTr("Ngôn ngữ và giọng")
                color: Theme.text
                font.pixelSize: Theme.body
                font.weight: Font.DemiBold
                textFormat: Text.PlainText
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.divider }

            Text {
                Layout.fillWidth: true
                text: AppController.processingDevice === "gpu"
                ? qsTr("Chế độ GPU: có thể chọn model GPU hoặc CPU.")
                    : qsTr("Chế độ CPU: model GPU chưa khả dụng. Đổi bộ xử lý trong Cài đặt → Chung để sử dụng GPU.")
                color: Theme.textMuted
                font.pixelSize: TypeScale.metadata
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
            }

            SettingLabel {
                Layout.fillWidth: true
                text: qsTr("Nhận dạng giọng nói")
                helpText: qsTr("Turbo cần GPU NVIDIA. Small dùng được trên CPU và GPU.")
            }
            StudioComboBox {
                Layout.fillWidth: true
                enabled: root.editable
                textRole: "label"
                valueRole: "value"
                model: root.speechRecognitionOptions
                currentIndex: root.speechRecognitionIndex
                onActivated: root.speechRecognitionEdited(currentValue)
            }

            SettingLabel {
                Layout.fillWidth: true
                text: qsTr("Model dịch")
                helpText: qsTr("HY-MT2 chạy cục bộ. Gemini và DeepSeek cần Internet và API key riêng; dịch qua API có thể tính phí theo mức sử dụng.")
            }
            TranslationModelCombo {
                Layout.fillWidth: true
                enabled: root.editable && !AppController.isProcessing
                selectedModel: root.translationModel
                onEdited: function(value) { root.translationModelEdited(value) }
            }

            SettingLabel {
                Layout.fillWidth: true
                text: qsTr("Dịch sang")
            }
            SearchableLanguageCombo {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                enabled: root.editable
                options: root.targetLanguageOptions
                selectedCode: root.targetLanguage
                onSelected: function(code) { root.targetLanguageEdited(code) }
            }

            SettingLabel {
                Layout.fillWidth: true
                text: qsTr("Công cụ giọng đọc")
                visible: root.ttsProviderOptions && root.ttsProviderOptions.length > 1
            }
            StudioComboBox {
                Layout.fillWidth: true
                enabled: root.editable
                visible: root.ttsProviderOptions && root.ttsProviderOptions.length > 1
                model: root.ttsProviderOptions
                textRole: "label"
                valueRole: "provider"
                currentIndex: root.ttsProviderIndex
                onActivated: root.ttsProviderEdited(currentValue)
            }
            SettingLabel {
                Layout.fillWidth: true
                text: qsTr("Phân vai người nói")
                helpText: qsTr("Chọn 1 người thuyết minh toàn bộ hoặc tự động nhận diện Nam ↔ Nữ cho video có 2 người nói.")
            }
            SegmentedControl {
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                enabled: root.editable
                currentValue: root.speakerMode === "multiple" ? "multiple" : "single"
                options: [
                    { "label": qsTr("Thuyết minh 1 người"), "value": "single" },
                    { "label": qsTr("Đối thoại 2 người (Nam ↔ Nữ)"), "value": "multiple" }
                ]
                onActivated: function(value) { root.speakerModeEdited(value) }
            }
            SettingLabel {
                Layout.fillWidth: true
                visible: root.speakerMode !== "multiple"
                text: qsTr("Giọng đọc")
                helpText: qsTr("25 giọng đọc chuẩn Bắc, Trung, Nam cùng tính năng nhân bản giọng đọc từ mẫu âm thanh của bạn.")
            }
            VoicePicker {
                Layout.fillWidth: true
                visible: root.speakerMode !== "multiple"
                enabled: root.editable
                model: root.ttsVoiceOptions
                currentValue: root.ttsVoice
                allowMultipleSpeakers: false
                allowVoiceClone: true
                previewSource: root.voicePreviewSource
                previewState: root.voicePreviewState
                onSelected: function(voice) {
                    root.ttsVoiceEdited(voice);
                }
                onPreviewRequested: function(voice) { root.ttsVoicePreviewRequested(voice) }
                onCloneRequested: root.cloneVoiceRequested()
            }
            SettingLabel {
                Layout.fillWidth: true
                visible: root.speakerMode === "multiple"
                text: qsTr("Giọng Nữ (nhân vật Nữ)")
                helpText: qsTr("Chọn giọng đọc cho các câu thoại của nhân vật nữ trong video.")
            }
            VoicePicker {
                Layout.fillWidth: true
                visible: root.speakerMode === "multiple"
                enabled: root.editable
                model: root.femaleVoiceOptions && root.femaleVoiceOptions.length > 0 ? root.femaleVoiceOptions : root.ttsVoiceOptions
                currentValue: root.femaleVoice
                allowMultipleSpeakers: false
                allowVoiceClone: false
                previewSource: root.voicePreviewSource
                previewState: root.voicePreviewState
                onSelected: function(voice) {
                    root.femaleVoiceEdited(voice);
                }
                onPreviewRequested: function(voice) { root.ttsVoicePreviewRequested(voice) }
            }
            SettingLabel {
                Layout.fillWidth: true
                visible: root.speakerMode === "multiple"
                text: qsTr("Giọng Nam (nhân vật Nam)")
                helpText: qsTr("Chọn giọng đọc cho các câu thoại của nhân vật nam trong video.")
            }
            VoicePicker {
                Layout.fillWidth: true
                visible: root.speakerMode === "multiple"
                enabled: root.editable
                model: root.maleVoiceOptions && root.maleVoiceOptions.length > 0 ? root.maleVoiceOptions : root.ttsVoiceOptions
                currentValue: root.maleVoice
                allowMultipleSpeakers: false
                allowVoiceClone: false
                previewSource: root.voicePreviewSource
                previewState: root.voicePreviewState
                onSelected: function(voice) {
                    root.maleVoiceEdited(voice);
                }
                onPreviewRequested: function(voice) { root.ttsVoicePreviewRequested(voice) }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: multiSpeakerRow.implicitHeight + Theme.space8 * 2
                visible: root.speakerMode === "multiple"
                radius: Theme.radiusSmall
                color: Theme.interactiveMuted
                border.width: 1
                border.color: Theme.outline

                RowLayout {
                    id: multiSpeakerRow
                    anchors.fill: parent
                    anchors.margins: Theme.space8
                    spacing: Theme.space8

                    AppIcon {
                        glyph: "\uE946"
                        iconSize: Theme.iconMedium
                        iconColor: Theme.primary
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("AI tự động nhận diện câu của Nam và Nữ trong video gốc. Nhân vật Nữ sẽ lồng giọng %1, nhân vật Nam sẽ lồng giọng %2.").arg(root.femaleVoice || "Trúc Ly").arg(root.maleVoice || "Hải Đăng")
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: TypeScale.caption
                        wrapMode: Text.Wrap
                    }
                }
            }

        }
    }

    Item {
        Layout.fillWidth: true
        Layout.fillHeight: root.columns === 2
        Layout.alignment: Qt.AlignTop
        implicitHeight: mediaColumn.implicitHeight

        ColumnLayout {
            id: mediaColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: Theme.space4
            anchors.rightMargin: Theme.space4
            spacing: root.mediaSpacing

            Text {
                text: qsTr("Hình ảnh và âm thanh")
                color: Theme.text
                font.pixelSize: Theme.body
                font.weight: Font.DemiBold
                textFormat: Text.PlainText
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.divider }

            RowLayout {
                Layout.fillWidth: true
                SettingLabel {
                    Layout.fillWidth: true
                    text: qsTr("Phụ đề gốc")
                }
                StudioButton {
                    text: qsTr("Chỉnh phụ đề")
                    enabled: root.editable && root.hasSource
                    onClicked: root.subtitleLayoutRequested()
                }
            }
            RowLayout {
                Layout.fillWidth: true
                SettingLabel {
                    Layout.fillWidth: true
                    text: qsTr("Chữ Trung Quốc")
                    helpText: qsTr("Tự quét mọi chữ Trung Quốc xuất hiện trên video (tiêu đề, tên kênh, sticker, phụ đề) và làm mờ đúng lúc chúng hiện.")
                }
                StudioButton {
                    objectName: "chineseTextButton"
                    text: qsTr("Xem & chọn vùng mờ")
                    enabled: root.hasSource
                    onClicked: chineseTextDialog.open()
                }
            }
            ChineseTextDialog { id: chineseTextDialog }
            SegmentedControl {
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                enabled: root.editable
                currentValue: root.removeOriginalSubtitles ? "remove" : "keep"
                options: [
                    { "label": qsTr("Che phụ đề gốc"), "value": "remove" },
                    { "label": qsTr("Giữ nguyên video gốc"), "value": "keep" }
                ]
                onActivated: function(value) { root.removeOriginalSubtitlesEdited(value === "remove") }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: root.removeOriginalSubtitles
                spacing: Theme.space8
                SettingLabel {
                    text: qsTr("Cách xóa")
                    helpText: qsTr("Làm mờ làm nhòe chữ được nhận diện. Vá nền dùng vùng ảnh sạch lân cận để lấp chữ.")
                }
                SegmentedControl {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    enabled: root.editable
                    currentValue: root.subtitleRemovalMode
                    options: [
                        { "label": qsTr("Làm mờ"), "value": "blur" },
                        { "label": qsTr("Vá nền lân cận"), "value": "patch" }
                    ]
                    onActivated: function(value) { root.subtitleRemovalModeEdited(value) }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.divider }

            SettingLabel {
                Layout.fillWidth: true
                text: qsTr("Nguồn âm thanh")
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space8
                SegmentedControl {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    enabled: root.editable
                    currentValue: root.enableAudioSeparation ? "separated" : "original"
                    options: [
                        { "label": qsTr("Giữ âm thanh gốc"), "value": "original" },
                        { "label": qsTr("Tách giọng"), "value": "separated" }
                    ]
                    onActivated: function(value) { root.audioSeparationEdited(value === "separated") }
                }
                StudioButton {
                    text: qsTr("Âm lượng")
                    variant: "secondary"
                    compact: true
                    enabled: root.editable
                    onClicked: root.audioMixRequested()
                }
            }
            Text {
                Layout.fillWidth: true
                visible: root.cpuOnly && root.enableAudioSeparation
                text: qsTr("Tách âm sẽ chậm hơn khi chạy bằng CPU")
                color: Theme.warning
                font.pixelSize: Theme.label
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space8
                SettingLabel {
                    Layout.fillWidth: true
                    text: qsTr("Nhạc nền")
                }
                StudioButton { text: qsTr("Tệp"); enabled: root.editable; onClicked: root.backgroundMusicFileRequested() }
                StudioButton { text: qsTr("Liên kết"); enabled: root.editable; onClicked: root.backgroundMusicLinkRequested() }
                StudioIconButton {
                    visible: root.backgroundMusicPath.length > 0
                    iconName: "delete"
                    toolTipText: qsTr("Bỏ nhạc nền")
                    enabled: root.editable
                    onClicked: root.backgroundMusicClearRequested()
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.backgroundMusicPath.length > 0 ? root.backgroundMusicPath : qsTr("Chưa có nhạc nền")
                color: root.backgroundMusicPath.length > 0 ? Theme.text : Theme.textMuted
                font.pixelSize: Theme.label
                elide: Text.ElideMiddle
            }

            MusicPlaybackSettings {
                Layout.fillWidth: true
                compact: root.availableHeight < 580
                visible: root.showMusicPlaybackSettings
                editable: root.editable
                hasMusic: root.backgroundMusicPath.length > 0
                loopMusic: root.backgroundMusicLoop
                ducking: root.audioDuckingEnabled
                reductionDb: root.audioDuckingReductionDb
                onLoopEdited: function(value) { root.backgroundMusicLoopEdited(value) }
                onDuckingEdited: function(value) { root.audioDuckingEdited(value) }
                onReductionEdited: function(value) { root.audioDuckingReductionEdited(value) }
                onMusicRequired: AppController.appAlertRequested(qsTr("Nhạc nền"), qsTr("Hãy nhập nhạc nền trước."), "info")
            }

            RowLayout {
                Layout.fillWidth: true
                SettingLabel {
                    Layout.fillWidth: true
                    text: qsTr("Watermark")
                }
                StudioButton {
                    objectName: "autoWatermarkEditButton"
                    text: qsTr("Chỉnh sửa")
                    enabled: root.editable
                    onClicked: root.watermarkRequested()
                }
            }
            SegmentedControl {
                Layout.fillWidth: true
                enabled: root.editable
                currentValue: root.watermarkKind
                options: [
                    { "label": qsTr("Chữ"), "value": "text" },
                    { "label": qsTr("Ảnh"), "value": "image" },
                    { "label": qsTr("Video"), "value": "video" }
                ]
                onActivated: function(value) { root.watermarkKindEdited(value) }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space8
                Text {
                    Layout.fillWidth: true
                    text: root.watermarkKind === "image"
                        ? (root.watermarkImagePath.length > 0 ? qsTr("Ảnh watermark") : qsTr("Chưa chọn ảnh"))
                        : root.watermarkKind === "video"
                            ? (root.watermarkVideoPath.length > 0 ? qsTr("Video watermark") : qsTr("Chưa chọn video"))
                            : (root.watermarkText.length > 0 ? root.watermarkText : qsTr("Không có watermark"))
                    color: (root.watermarkKind === "image" && root.watermarkImagePath.length > 0)
                        || (root.watermarkKind === "video" && root.watermarkVideoPath.length > 0)
                        || (root.watermarkKind === "text" && root.watermarkText.length > 0)
                        ? Theme.text : Theme.textMuted
                    font.pixelSize: Theme.label
                    elide: Text.ElideRight
                }
            }
        }
    }
}
