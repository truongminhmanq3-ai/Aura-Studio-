pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import "."

ColumnLayout {
    id: root
    property bool keyVisible: false
    property string draftModel: AppController.elevenLabsModel
    spacing: Theme.space16
    Text {
        Layout.fillWidth: true
        text: qsTr("ElevenLabs · Tạo giọng đọc")
        color: Theme.text
        font.pixelSize: TypeScale.title
        font.weight: Font.DemiBold
    }
    Text {
        Layout.fillWidth: true
        text: qsTr("Chọn ElevenLabs trong mục Công cụ giọng đọc của dự án để sử dụng. Nội dung cần đọc sẽ được gửi đến ElevenLabs và sử dụng credit của tài khoản. OmniVoice vẫn dùng được cục bộ.")
        color: Theme.textMuted
        font.pixelSize: TypeScale.body
        wrapMode: Text.WordWrap
    }
    SettingsGroup {
        Layout.fillWidth: true
        title: qsTr("API key")
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space12
            Text {
                Layout.fillWidth: true
                text: AppController.elevenLabsKeyConfigured ? qsTr("Đã lưu API key trên máy") : qsTr("Chưa có API key")
                color: Theme.textMuted
                font.pixelSize: TypeScale.body
            }
            RowLayout {
                Layout.fillWidth: true
                AppTextField {
                    id: keyInput
                    objectName: "elevenLabsApiKeyInput"
                    Layout.fillWidth: true
                    accessibleName: qsTr("ElevenLabs API key")
                    placeholderText: qsTr("Dán ElevenLabs API key")
                    echoMode: root.keyVisible ? TextInput.Normal : TextInput.Password
                    inputMethodHints: Qt.ImhHiddenText | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                    enabled: !AppController.elevenLabsBusy
                }
                StudioButton {
                    text: root.keyVisible ? qsTr("Ẩn") : qsTr("Hiện")
                    enabled: keyInput.text.length > 0
                    onClicked: root.keyVisible = !root.keyVisible
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space8
                StudioButton {
                    objectName: "saveElevenLabsApiKeyButton"
                    text: qsTr("Lưu key và tải giọng")
                    variant: "primary"
                    enabled: !AppController.elevenLabsBusy && keyInput.text.trim().length > 0
                    onClicked: if (AppController.saveElevenLabsApiKey(keyInput.text)) { keyInput.clear(); root.keyVisible = false; }
                }
                StudioButton {
                    text: qsTr("Lấy API key")
                    onClicked: AppController.openElevenLabsApiKeys()
                }
                StudioButton {
                    text: qsTr("Xóa key")
                    enabled: AppController.elevenLabsKeyConfigured && !AppController.elevenLabsBusy
                    onClicked: AppController.clearElevenLabsApiKey()
                }
            }
            Text {
                Layout.fillWidth: true
                text: qsTr("Key được lưu trong kho bảo mật của hệ điều hành (Keychain trên Mac), không lưu trong dự án. Key cần quyền Text to Speech và Voices để tải danh sách giọng.")
                color: Theme.textSubtle
                font.pixelSize: TypeScale.metadata
                wrapMode: Text.WordWrap
            }
            Text {
                objectName: "elevenLabsConnectionStatus"
                Layout.fillWidth: true
                text: AppController.elevenLabsMessage
                visible: text.length > 0
                color: Theme.textMuted
                font.pixelSize: TypeScale.body
                wrapMode: Text.WordWrap
            }
        }
    }
    SettingsGroup {
        Layout.fillWidth: true
        title: qsTr("Giọng mặc định và model")
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space12
            SettingLabel { text: qsTr("Giọng trong tài khoản") }
            RowLayout {
                Layout.fillWidth: true
                StudioComboBox {
                    objectName: "elevenLabsAccountVoicePicker"
                    Layout.fillWidth: true
                    model: AppController.elevenLabsVoices
                    textRole: "label"
                    valueRole: "voice"
                    onActivated: voiceId.text = String(currentValue).replace("elevenlabs:", "")
                }
                StudioButton {
                    text: AppController.elevenLabsBusy ? qsTr("Đang tải…") : qsTr("Tải lại giọng")
                    enabled: AppController.elevenLabsKeyConfigured && !AppController.elevenLabsBusy
                    onClicked: AppController.refreshElevenLabsVoices()
                }
            }
            SettingLabel { text: qsTr("Voice ID (có thể dán trực tiếp)") }
            AppTextField {
                id: voiceId
                objectName: "elevenLabsVoiceIdInput"
                Layout.fillWidth: true
                text: AppController.elevenLabsVoiceId
                accessibleName: qsTr("ElevenLabs Voice ID")
                placeholderText: qsTr("Voice ID từ ElevenLabs")
            }
            SettingLabel { text: qsTr("Model") }
            StudioComboBox {
                objectName: "elevenLabsModelPicker"
                Layout.fillWidth: true
                model: [{label: "Flash v2.5 · Tiếng Việt · Nhanh", value: "eleven_flash_v2_5"},
                        {label: "Eleven v3 · Giàu biểu cảm", value: "eleven_v3"}]
                textRole: "label"
                valueRole: "value"
                currentIndex: root.draftModel === "eleven_v3" ? 1 : 0
                onActivated: root.draftModel = currentValue
            }
            StudioButton {
                objectName: "saveElevenLabsVoiceSettingsButton"
                text: qsTr("Lưu giọng và model")
                enabled: voiceId.text.trim().length > 0 && !AppController.elevenLabsBusy
                onClicked: AppController.saveElevenLabsVoiceSettings(voiceId.text, root.draftModel)
            }
            Text {
                Layout.fillWidth: true
                text: qsTr("Giọng đã nhân bản trên ElevenLabs cũng xuất hiện trong danh sách tài khoản. Bạn chọn giọng riêng cho từng dự án ở mục Giọng đọc.")
                color: Theme.textMuted
                font.pixelSize: TypeScale.metadata
                wrapMode: Text.WordWrap
            }
        }
    }
    onVisibleChanged: if (!visible) { keyInput.clear(); keyVisible = false; }
}
