pragma ComponentBehavior: Bound
// qmllint disable missing-property
import QtQuick
import QtQuick.Layouts
import "."

Item {
    id: root
    property string provider: "gemini"
    property bool editingKey: false
    readonly property bool elevenlabs: provider === "elevenlabs"
    readonly property bool deepseek: provider === "deepseek"
    readonly property bool customProvider: elevenlabs || deepseek
    readonly property var apiKeys: customProvider ? [] : AppController.geminiApiKeys
    readonly property bool configured: apiKeys.length > 0
    onProviderChanged: { entryForm.clear(); editingKey = false; }
    onVisibleChanged: { if (!visible) { entryForm.clear(); editingKey = false; } }

    Connections {
        target: AppController
        function onApiKeySettingsRequested(provider) { root.provider = provider; }
        function onApiKeyGuideRequested(provider) {
            root.provider = provider;
            Qt.callLater(function() {
                geminiGuideLoader.invoke("open", []);
            });
        }
        function onGeminiSetupRequested() { root.provider = "gemini"; }
    }
    SettingsPageShell {
        anchors.fill: parent
        showHeader: false
        pageInset: 0
        horizontalInset: 0
        alignLeft: false
        contentMaximumWidth: 760
        contentSpacing: Theme.space20

        NavigationTabs {
            objectName: "apiKeyProviderSelector"
            options: [{ label: "Gemini", value: "gemini" },
                      { label: "DeepSeek", value: "deepseek" }]
            currentValue: root.provider
            onActivated: function(value) { root.provider = value; }
        }
        DeepSeekSettingsPanel {
            Layout.fillWidth: true
            visible: root.deepseek
        }
        ElevenLabsSettingsPanel {
            Layout.fillWidth: true
            visible: root.elevenlabs
        }
        RowLayout {
            visible: !root.customProvider
            Layout.fillWidth: true
            spacing: Theme.space16
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space8
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Gemini API key")
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.title
                    font.weight: Font.DemiBold
                }
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Dịch bằng Gemini. Chọn model trong dự án.")
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.body
                    wrapMode: Text.WordWrap
                }
            }
            StudioButton {
                objectName: "apiKeyGuideButton"
                text: qsTr("Hướng dẫn")
                onClicked: geminiGuideLoader.invoke("open", [])
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: !root.customProvider && !root.configured
            spacing: Theme.space8
            Text {
                objectName: "credentialStatus"
                Layout.fillWidth: true
                text: qsTr("Chưa có key. Bạn vẫn có thể dùng model dịch cục bộ.")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: TypeScale.body
                wrapMode: Text.WordWrap
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space12
            visible: !root.customProvider && root.configured
            Repeater {
                model: root.apiKeys
                delegate: ApiKeyListRow {
                    required property var modelData
                    Layout.fillWidth: true
                    credential: modelData
                    onRemoveRequested: function(id, label) { removeLoader.invoke("confirm", [id, label]); }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: !root.customProvider && root.configured && !root.editingKey
            spacing: Theme.space8
            StudioButton {
                objectName: "editApiKeyButton"
                text: qsTr("Thêm key")
                onClicked: root.editingKey = true
            }
        }
        ApiKeyEntryForm {
            id: entryForm
            objectName: "apiKeyEntryForm"
            Layout.fillWidth: true
            visible: !root.customProvider && (root.editingKey || !root.configured)
            onAccepted: root.editingKey = false
            onCancelled: root.editingKey = false
        }
        Item { Layout.preferredHeight: Theme.space16 }
    }
    LazyDialogLoader {
        id: geminiGuideLoader
        sourceComponent: Component { GeminiApiGuideDialog { onClosed: geminiGuideLoader.release() } }
    }
    LazyDialogLoader {
        id: removeLoader
        sourceComponent: Component {
            AppDialog {
                id: dialog
                property string keyId: ""
                function confirm(id, label) { keyId = id; subtitle = label; open(); }
                title: qsTr("Xóa API key?")
                preferredWidth: 440
                onClosed: removeLoader.release()
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Chỉ xóa key trên máy này. Dự án và tài khoản trên dịch vụ vẫn được giữ nguyên.")
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.label
                    wrapMode: Text.WordWrap
                }
                footerActions: [
                    StudioButton { text: qsTr("Hủy"); onClicked: dialog.close() },
                    StudioButton {
                        text: qsTr("Xóa key")
                        variant: "danger"
                        onClicked: {
                            const removed = AppController.removeGeminiApiKey(dialog.keyId);
                            if (removed) dialog.close();
                        }
                    }
                ]
            }
        }
    }
}
