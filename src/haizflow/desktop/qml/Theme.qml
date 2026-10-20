pragma Singleton
import QtQuick

QtObject {
    property bool motionEnabled: true

    readonly property string fontFamily: ".AppleSystemUIFont"

    // Apple Pure White & Space Black (Light Monochrome) Liquid Glass palette.
    readonly property color window: "#FFFFFF"
    readonly property color surface: "#FFFFFF"
    readonly property color surfaceElevated: "#FFFFFF"
    readonly property color surfaceMuted: "#FBFBFD"
    readonly property color surfaceStrong: "#F5F5F7"
    readonly property color input: "#FFFFFF"
    readonly property color sidebar: "#FBFBFD"
    readonly property color sidebarHover: "#F5F5F7"
    readonly property color sidebarSelected: "#FFFFFF"
    readonly property color topBar: "#FFFFFF"
    readonly property color windowCaptionHover: "#F5F5F7"
    readonly property color windowCaptionPressed: "#EBEBF0"
    readonly property color windowCloseHover: "#FF3B30"
    readonly property color windowClosePressed: "#D70015"
    readonly property color outline: "#E5E5EA"
    readonly property color outlineStrong: "#D2D2D7"
    readonly property color divider: "#EBEBF0"

    readonly property color text: "#1D1D1F"
    readonly property color textMuted: "#6E6E73"
    readonly property color textSubtle: "#86868B"
    readonly property color textDisabled: "#AEAEB2"
    readonly property color textOnAccent: "#FFFFFF"
    readonly property color textOnDark: "#FFFFFF"
    readonly property color textOnDarkMuted: "#E5E5EA"

    readonly property color interactive: "#1D1D1F"
    readonly property color interactiveHover: "#333336"
    readonly property color interactivePressed: "#000000"
    readonly property color interactiveMuted: "#F5F5F7"
    readonly property color interactiveOutline: "#86868B"
    readonly property color focus: "#1D1D1F"

    readonly property color amber: "#1D1D1F"
    readonly property color amberMuted: "#F5F5F7"
    readonly property color warmSurface: "#FBFBFD"
    readonly property color danger: "#FF3B30"
    readonly property color dangerMuted: "#FFEBEA"
    readonly property color success: "#1D1D1F"
    readonly property color successMuted: "#F5F5F7"
    readonly property color warning: "#333336"
    readonly property color warningMuted: "#F5F5F7"
    readonly property color scrim: "#40000000"
    readonly property color video: "#FFFFFF"
    readonly property color codeSurface: "#FBFBFD"
    readonly property color codeText: "#1D1D1F"
    readonly property color captionOverlay: "#D91D1D1F"
    readonly property color captionText: "#FFFFFF"

    readonly property int radius: 24
    readonly property int radiusSmall: 18
    readonly property int radiusTiny: 12

    readonly property int space4: 4
    readonly property int space8: 8
    readonly property int space12: 12
    readonly property int space16: 16
    readonly property int space20: 20
    readonly property int space24: 24
    readonly property int space32: 32
    readonly property int gap: space16

    readonly property int label: TypeScale.metadata
    readonly property int caption: TypeScale.label
    readonly property int body: TypeScale.control
    readonly property int bodyLarge: TypeScale.body
    readonly property int h3: TypeScale.section
    readonly property int h2: TypeScale.title
    readonly property int h1: TypeScale.pageTitle
    readonly property int display: TypeScale.display

    readonly property int iconSmall: 14
    readonly property int icon: 16
    readonly property int iconLarge: 20
    readonly property string iconFont: ".AppleSystemUIFont"

    readonly property int motionFast: motionEnabled ? Motion.fast : 0
    readonly property int motionStandard: motionEnabled ? Motion.standard : 0
    readonly property int motionSlow: motionEnabled ? Motion.slow : 0
    readonly property int navigationExpanded: UiMetrics.navigationExpanded
    readonly property int navigationCompact: UiMetrics.navigationCompact
    readonly property int commandBarHeight: 48
}
