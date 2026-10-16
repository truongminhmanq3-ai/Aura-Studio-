pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

ComboBox {
    id: root

    property string logoRole: ""
    property var logoModel: []
    implicitHeight: UiMetrics.controlHeight
    leftPadding: 12
    rightPadding: 38
    font.family: Theme.fontFamily
    font.pixelSize: TypeScale.control
    focusPolicy: Qt.TabFocus
    Accessible.name: displayText

    function logoAt(index) {
        if (!logoRole || index < 0 || !logoModel || logoModel[index] === undefined)
            return "";
        const entry = logoModel[index];
        if (typeof entry === "string")
            return entry;
        return entry && entry[logoRole] !== undefined ? String(entry[logoRole]) : "";
    }

    contentItem: RowLayout {
        spacing: 8

        PlatformLogo {
            Layout.preferredWidth: 22
            Layout.preferredHeight: 22
            platform: root.logoAt(root.currentIndex)
            visible: platform.length > 0
        }

        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            text: root.displayText
            color: root.enabled ? Theme.text : Theme.textDisabled
            font.family: root.font.family
            font.pixelSize: root.font.pixelSize
            fontSizeMode: Text.FixedSize
            verticalAlignment: Text.AlignVCenter
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
    }

    indicator: AppIcon {
        x: root.width - width - 12
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.icon
        height: Theme.icon
        glyph: root.popup.opened ? "\uE70E" : "\uE70D"
        iconColor: root.enabled ? Theme.textMuted : Theme.textDisabled
        iconSize: Theme.iconSmall
    }

    background: Rectangle {
        radius: Math.round(root.height / 2)
        color: "transparent"
        border.width: 1.5
        border.color: "#FFFFFF"
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.enabled && root.hovered ? "#48FFFFFF" : "#33FFFFFF" }
            GradientStop { position: 0.5; color: root.enabled && root.hovered ? "#18FFFFFF" : "#0DFFFFFF" }
            GradientStop { position: 1.0; color: root.enabled && root.hovered ? "#38FFFFFF" : "#28FFFFFF" }
        }
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.width: root.visualFocus || root.popup.opened ? 1.5 : 1
            border.color: root.visualFocus || root.popup.opened ? "#09090B"
                : (root.hovered ? "#42000000" : "#26000000")
        }
    }

    popup: Popup {
        id: voicePopup

        y: root.height + 6
        width: root.width
        height: Math.min(292, Math.max(52, voiceList.contentHeight + 16))
        padding: 8
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        onOpened: Qt.callLater(function() {
            if (voiceList.currentIndex >= 0)
                voiceList.positionViewAtIndex(voiceList.currentIndex, ListView.Contain);
        })

        enter: Transition {
            NumberAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: Theme.motionFast
            }
        }
        exit: Transition {
            NumberAnimation {
                property: "opacity"
                from: 1
                to: 0
                duration: Theme.motionFast
            }
        }

        contentItem: ListView {
            id: voiceList

            clip: true
            model: root.delegateModel
            // Include count in the binding so replacing an async model also
            // clamps/restores keyboard highlight and scroll position.
            currentIndex: Math.max(-1, Math.min(root.highlightedIndex, count - 1))
            reuseItems: true
            ScrollIndicator.vertical: ScrollIndicator {}
        }

        background: Rectangle {
            radius: 22
            border.width: 1.5
            border.color: "#FFFFFF"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FAFFFFFF" }
                GradientStop { position: 1.0; color: "#F2F4F6FA" }
            }
            Rectangle {
                anchors.fill: parent
                radius: 22
                color: "transparent"
                border.width: 1
                border.color: "#22000000"
            }
        }
    }

    delegate: ItemDelegate {
        id: voiceDelegate

        required property int index
        required property var modelData
        readonly property bool optionAvailable: !voiceDelegate.modelData || voiceDelegate.modelData.available === undefined || voiceDelegate.modelData.available !== false
        readonly property string optionCategory: voiceDelegate.modelData && voiceDelegate.modelData.category !== undefined ? String(voiceDelegate.modelData.category) : ""
        readonly property bool showCategory: optionCategory.length > 0 && (voiceDelegate.index === 0 || !root.model[voiceDelegate.index - 1] || String(root.model[voiceDelegate.index - 1].category || "") !== optionCategory)

        width: root.popup.width - 12
        height: 40 + (showCategory ? 26 : 0)
        enabled: voiceDelegate.optionAvailable
        highlighted: voiceDelegate.enabled && root.highlightedIndex === voiceDelegate.index

        contentItem: ColumnLayout {
            spacing: 0

            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: voiceDelegate.showCategory ? 26 : 0
                visible: voiceDelegate.showCategory
                text: String(voiceDelegate.modelData.categoryLabel || voiceDelegate.optionCategory)
                color: Theme.textSubtle
                font.family: Theme.fontFamily
                font.pixelSize: TypeScale.metadata
                font.weight: Font.DemiBold
                verticalAlignment: Text.AlignBottom
                leftPadding: 8
                textFormat: Text.PlainText
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8

                PlatformLogo {
                    Layout.preferredWidth: 22
                    Layout.preferredHeight: 22
                    platform: root.logoAt(voiceDelegate.index)
                    visible: platform.length > 0
                }

                Text {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    text: root.textAt(voiceDelegate.index)
                    color: !voiceDelegate.enabled ? Theme.textDisabled : (voiceDelegate.highlighted ? Theme.interactive : Theme.text)
                    font.family: Theme.fontFamily
                    font.pixelSize: TypeScale.control
                    fontSizeMode: Text.FixedSize
                    font.weight: voiceDelegate.highlighted ? Font.DemiBold : Font.Normal
                    verticalAlignment: Text.AlignVCenter
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }
            }
        }

        background: Rectangle {
            radius: Theme.radiusSmall
            color: voiceDelegate.highlighted ? Theme.interactiveMuted : "transparent"
        }
    }
}
