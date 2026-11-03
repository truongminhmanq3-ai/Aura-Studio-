pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "."

AppDialog {
    id: root

    property bool replacingVoice: false
    property string draftProvider: "omnivoice"
    property string draftVoice: ""
    property string draftSpeakerMode: "single"
    property string globalProvider: "omnivoice"
    property string globalVoice: ""
    property string openedVideoId: ""
    property var voiceModel: []

    signal confirmed(string provider, string voice, string scope, string segmentId, string speakerMode)
    signal cloneRequested()

    title: replacingVoice ? qsTr("Đổi hoặc tạo lại giọng") : qsTr("Tạo giọng đọc")
    preferredWidth: 560
    maximumHeight: 680

    function firstAvailableVoice(options) {
        for (let index = 0; index < options.length; ++index) {
            if (options[index].available === undefined || options[index].available !== false)
                return String(options[index].voice || "");
        }
        return "";
    }

    function refreshVoices(preferredVoice) {
        const updatedOptions = AppController.manualVoiceOptionsForProvider(draftProvider);
        if (JSON.stringify(voiceModel) !== JSON.stringify(updatedOptions))
            voiceModel = updatedOptions;
        const requested = String(preferredVoice || "");
        for (let index = 0; index < voiceModel.length; ++index) {
            if (String(voiceModel[index].voice || "") === requested
                    && (voiceModel[index].available === undefined || voiceModel[index].available !== false)) {
                draftVoice = requested;
                return;
            }
        }
        draftVoice = firstAvailableVoice(voiceModel);
    }

    function openForVoice(hasVoice, configuration) {
        openedVideoId = String(AppController.selectedVideoId || "");
        replacingVoice = Boolean(hasVoice);
        globalProvider = String(configuration.globalProvider || configuration.provider || "omnivoice");
        globalVoice = String(configuration.globalVoice || configuration.voice || "");
        draftSpeakerMode = String(configuration.speakerMode || "single");
        draftProvider = globalProvider;
        refreshVoices(globalVoice);
        open();
    }

    function selectCloneReference() {
        draftSpeakerMode = "single";
        draftProvider = AppController.ttsProvider;
        globalProvider = draftProvider;
        globalVoice = "omnivoice:clone";
        refreshVoices("omnivoice:clone");
    }

    onClosed: voicePicker.stopPreview()

    Connections {
        target: AppController

        function onSelectedVideoChanged() {
            if (!root.opened)
                return;
            if (String(AppController.selectedVideoId || "") !== root.openedVideoId) {
                root.close();
                return;
            }
            // Refresh availability while preserving the user's draft. Only
            // an explicit Apply action in the recorder chooses Clone.
            root.refreshVoices(root.draftVoice);
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Theme.space16

        GridLayout {
            Layout.fillWidth: true
            columns: 1
            columnSpacing: Theme.space12
            rowSpacing: Theme.space8

            SettingLabel {
                text: qsTr("Công cụ")
                visible: AppController.ttsProviderOptions && AppController.ttsProviderOptions.length > 1
            }
            StudioComboBox {
                Layout.fillWidth: true
                visible: AppController.ttsProviderOptions && AppController.ttsProviderOptions.length > 1
                model: AppController.ttsProviderOptions
                textRole: "label"
                valueRole: "provider"
                currentIndex: {
                    for (let i = 0; i < model.length; ++i) {
                        if (model[i].provider === root.draftProvider)
                            return i;
                    }
                    return 0;
                }
                onActivated: {
                    root.draftProvider = currentValue;
                    root.draftSpeakerMode = "single";
                    root.refreshVoices(root.draftVoice);
                }
            }

            SettingLabel {
                Layout.fillWidth: true
                text: qsTr("Giọng đọc")
                helpText: qsTr("25 giọng đọc chuẩn Bắc, Trung, Nam cùng tính năng nhân bản giọng đọc từ mẫu âm thanh của bạn.")
            }

            VoicePicker {
                id: voicePicker
                Layout.fillWidth: true
                model: root.voiceModel
                currentValue: root.draftVoice
                allowMultipleSpeakers: false
                allowVoiceClone: true
                onCloneRequested: root.cloneRequested()
                previewEnabled: true
                previewSource: AppController.audioPreviewSource
                previewState: AppController.audioPreviewState
                onSelected: function(voice) {
                    root.draftVoice = voice;
                }
                onPreviewRequested: function(voice) {
                    AppController.previewVoiceSample(
                        root.draftProvider,
                        voice,
                        AppController.targetLanguage
                    );
                }
            }
        }

    }

    footerActions: [
        StudioButton {
            text: qsTr("Hủy")
            variant: "secondary"
            onClicked: root.close()
        },
        StudioButton {
            text: qsTr("Tạo giọng")
            iconName: "play"
            variant: "primary"
            enabled: root.draftVoice.length > 0
            onClicked: {
                root.confirmed(
                    root.draftProvider,
                    root.draftVoice,
                    "all",
                    "",
                    root.draftSpeakerMode
                );
                root.close();
            }
        }
    ]
}
