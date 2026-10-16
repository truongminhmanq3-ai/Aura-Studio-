pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: root

    width: 1440
    height: 900
    minimumWidth: 1120
    minimumHeight: 720
    visible: false
    flags: Qt.Window
    title: "Aura Studio"
    color: Theme.window
    topPadding: 0
    leftPadding: 0
    rightPadding: 0
    bottomPadding: 0

    readonly property string routeHome: "home"
    readonly property string routeProjects: "projects"
    readonly property string routeSettings: "settings"
    readonly property string routeApiKeys: "api-keys"
    readonly property string routePackages: "packages"
    readonly property string routeSingleProjects: "single-projects"
    readonly property string routeSingleWorkspace: "single-workspace"
    readonly property string routeManualProjects: "manual-projects"
    readonly property string routeManualWorkspace: "manual-workspace"
    readonly property string routeBatchProjects: "batch-projects"
    readonly property string routeBatchWorkspace: "batch-workspace"
    readonly property string routeBatchVideo: "batch-video"
    readonly property string routeDownloadProjects: "download-projects"
    readonly property string routeDownloadWorkspace: "download-workspace"
    readonly property string routePublishProjects: "publish-projects"
    readonly property string routePublishWorkspace: "publish-workspace"
    property string currentRoute: routeHome
    property string workspaceReturnRoute: routeHome
    property var routeHistory: [routeHome]
    property int routeHistoryIndex: 0
    readonly property bool compactNavigation: width < 1280
    readonly property bool videoProcessing: AppController.isProcessing && !AppController.isSwitchingProcessingDevice
    // qmllint disable stale-property-read
    readonly property var downloader: AppController.mediaDownloader
    // qmllint enable stale-property-read
    readonly property bool selectedTaskFailed: projectWorkspaceVisible
        && AppController.selectedStatus === "failed"
    readonly property bool selectedTaskPaused: projectWorkspaceVisible
        && AppController.selectedStatus === "paused"
    readonly property bool selectedTaskQueued: projectWorkspaceVisible
        && AppController.isSelectedVideoQueued && !AppController.isSelectedVideoProcessing
    readonly property bool selectedProgressMeasured: [
        "extracting_audio", "separating_audio", "transcribing",
        "creating_subtitle", "building_audio_timeline",
        "manual_source", "manual_separation", "manual_recognition", "manual_audio"
    ].indexOf(AppController.selectedStepId) < 0
    readonly property bool routeCanGoBack: routeHistoryIndex > 0
    readonly property bool routeCanGoForward: routeHistoryIndex < routeHistory.length - 1
    readonly property bool projectWorkspaceVisible: currentRoute === routeSingleWorkspace || currentRoute === routeManualWorkspace || currentRoute === routeBatchWorkspace || currentRoute === routeBatchVideo || currentRoute === routeDownloadWorkspace || currentRoute === routePublishWorkspace
    readonly property bool globalNavigationBlocked: lazyDialogVisible(projectSetupDialogLoader) || lazyDialogVisible(urlImportDialogLoader) || lazyDialogVisible(downloadProjectSourceDialogLoader) || lazyDialogVisible(batchSettingsDialogLoader) || lazyDialogVisible(translationReviewDialogLoader) || appAlertDialog.visible || modelSetupOverlayLoader.active
    readonly property bool downloadCanGoBack: routeHost.downloadCanGoBack
    readonly property bool downloadCanGoForward: routeHost.downloadCanGoForward
    readonly property bool canNavigateBack: !globalNavigationBlocked && (downloadCanGoBack || routeCanGoBack)
    readonly property bool canNavigateForward: !globalNavigationBlocked && (downloadCanGoForward || routeCanGoForward)
    readonly property bool editScopeAvailable: currentRoute === routeSettings || currentRoute === routeApiKeys || currentRoute === routePackages
        || currentRoute === routeSingleWorkspace
        || currentRoute === routeManualWorkspace
        || currentRoute === routeBatchWorkspace
        || currentRoute === routeBatchVideo
        || currentRoute === routeDownloadWorkspace
        || currentRoute === routePublishWorkspace

    function syncEditHistoryScope() {
        if (currentRoute === routeSettings || currentRoute === routeApiKeys || currentRoute === routePackages) {
            AppController.setEditHistoryScope("settings");
        } else if (currentRoute === routeBatchWorkspace
                || currentRoute === routeDownloadWorkspace
                || currentRoute === routePublishWorkspace) {
            AppController.setEditHistoryScope("project");
        } else if (currentRoute === routeSingleWorkspace
                || currentRoute === routeManualWorkspace
                || currentRoute === routeBatchVideo) {
            AppController.setEditHistoryScope("video");
        } else {
            AppController.setEditHistoryScope("none");
        }
    }

    onCurrentRouteChanged: syncEditHistoryScope()

    function navigationSection() {
        if (currentRoute === routeProjects)
            return "home";
        if (currentRoute === routeSingleProjects)
            return "single";
        if (currentRoute === routeManualProjects)
            return "manual";
        if (currentRoute === routeBatchProjects)
            return "batch";
        if (currentRoute === routeSettings || currentRoute === routeApiKeys || currentRoute === routePackages)
            return "settings";
        if (currentRoute === routeDownloadProjects)
            return "downloads";
        if (currentRoute === routePublishProjects)
            return "social";
        return "home";
    }

    function lazyDialogVisible(loader) {
        return loader.status === Loader.Ready && loader.item !== null && loader.item.visible;
    }

    // Reconcile in the background whenever the user returns from a browser.
    // This catches dashboard disconnects immediately without disabling the UI.
    onActiveChanged: {
        if (active && currentRoute === routePublishWorkspace && !AppController.tiktokPublishBusy)
            AppController.reconcileZernioConnections();
    }

    function routeIsAvailable(route) {
        if (route === routeHome || route === routeProjects || route === routeSettings || route === routeApiKeys || route === routePackages || route === routeSingleProjects || route === routeManualProjects || route === routeBatchProjects || route === routeDownloadProjects || route === routePublishProjects)
            return true;
        if (!AppController.hasOpenProject)
            return false;
        if (route === routeSingleWorkspace)
            return AppController.projectType === "single";
        if (route === routeManualWorkspace)
            return AppController.projectType === "manual";
        if (route === routeBatchWorkspace)
            return AppController.projectType === "batch";
        if (route === routeBatchVideo)
            return AppController.projectType === "batch" && AppController.isSelectedBatchVideo;
        if (route === routeDownloadWorkspace)
            return AppController.projectType === "download";
        if (route === routePublishWorkspace)
            return AppController.projectType === "publish";
        return false;
    }

    function resetRouteHistory(route) {
        routeHistory = [route];
        routeHistoryIndex = 0;
        currentRoute = route;
    }

    function pruneRouteHistory() {
        let filtered = [];
        let nextIndex = 0;
        for (let index = 0; index < routeHistory.length; ++index) {
            const route = routeHistory[index];
            if (!routeIsAvailable(route))
                continue;
            if (index <= routeHistoryIndex)
                nextIndex = filtered.length;
            filtered.push(route);
        }
        if (filtered.length === 0) {
            resetRouteHistory(workspaceReturnRoute);
            return;
        }
        routeHistory = filtered;
        routeHistoryIndex = Math.max(0, Math.min(nextIndex, filtered.length - 1));
        if (!routeIsAvailable(currentRoute))
            currentRoute = filtered[routeHistoryIndex];
    }

    function openProjectWorkspace(projectsRoute, workspaceRoute) {
        workspaceReturnRoute = projectsRoute;
        resetRouteHistory(projectsRoute);
        navigate(workspaceRoute);
    }

    function replaceCurrentRoute(route) {
        if (route === currentRoute)
            return;
        saveCurrentVideoSettings();
        let nextHistory = routeHistory.slice();
        nextHistory[routeHistoryIndex] = route;
        if (routeHistoryIndex > 0 && nextHistory[routeHistoryIndex - 1] === route) {
            nextHistory = nextHistory.slice(0, routeHistoryIndex);
            routeHistoryIndex = nextHistory.length - 1;
        }
        routeHistory = nextHistory;
        currentRoute = route;
    }

    function navigate(route) {
        if (route === currentRoute)
            return;
        if (!routeIsAvailable(route)) {
            pruneRouteHistory();
            return;
        }

        saveCurrentVideoSettings();
        let nextHistory = routeHistory.slice(0, routeHistoryIndex + 1);
        nextHistory.push(route);
        routeHistory = nextHistory;
        routeHistoryIndex = nextHistory.length - 1;
        currentRoute = route;
    }

    function navigateBack() {
        if (globalNavigationBlocked)
            return;
        if (downloadCanGoBack) {
            routeHost.navigateDownloadBack();
            return;
        }
        pruneRouteHistory();
        if (!routeCanGoBack)
            return;
        saveCurrentVideoSettings();
        routeHistoryIndex -= 1;
        currentRoute = routeHistory[routeHistoryIndex];
    }

    function navigateForward() {
        if (globalNavigationBlocked)
            return;
        if (downloadCanGoForward) {
            routeHost.navigateDownloadForward();
            return;
        }
        pruneRouteHistory();
        if (!routeCanGoForward)
            return;
        saveCurrentVideoSettings();
        routeHistoryIndex += 1;
        currentRoute = routeHistory[routeHistoryIndex];
    }

    function saveCurrentVideoSettings() {
        if (currentRoute === routeBatchVideo && AppController.isSelectedBatchVideo && !AppController.isSelectedVideoProcessing)
            AppController.persistSelectedBatchVideoSettings();
    }

    Component.onCompleted: {
        I18n.language = AppController.settingsLanguage;
        AppController.enableInAppAlerts();
        syncEditHistoryScope();
    }

    Binding {
        target: UiMetrics
        property: "viewportWidth"
        value: root.width
    }

    Binding {
        target: UiMetrics
        property: "viewportHeight"
        value: root.height
    }

    LazyDialogLoader {
        id: projectSetupDialogLoader
        sourceComponent: Component {
            ProjectSetupDialog { onClosed: projectSetupDialogLoader.release() }
        }
    }

    LazyDialogLoader {
        id: projectRenameDialogLoader
        sourceComponent: Component {
            ProjectRenameDialog { onClosed: projectRenameDialogLoader.release() }
        }
    }

    LazyDialogLoader {
        id: videoExportDialogLoader
        sourceComponent: Component { VideoExportDialog { onClosed: videoExportDialogLoader.release() } }
    }
    LazyDialogLoader {
        id: videoExportJobsDialogLoader
        sourceComponent: Component { VideoExportJobsDialog { onClosed: videoExportJobsDialogLoader.release() } }
    }
    Connections {
        target: AppController
        function onVideoExportRequested() { videoExportDialogLoader.invoke("openForSelection", []); }
        function onAutoProcessingRequested() { videoExportDialogLoader.invoke("openForProcessing", []); }
        function onBatchProcessingRequested(processFirst) { videoExportDialogLoader.invoke("openForBatch", [processFirst]); }
        function onVideoExportStarted() { videoExportJobsDialogLoader.invoke("open", []); }
    }

    LazyDialogLoader {
        id: urlImportDialogLoader
        sourceComponent: Component {
            UrlImportDialog { onClosed: urlImportDialogLoader.release() }
        }
    }

    LazyDialogLoader {
        id: downloadProjectSourceDialogLoader
        sourceComponent: Component {
            DownloadProjectSourceDialog { onClosed: downloadProjectSourceDialogLoader.release() }
        }
    }

    LazyDialogLoader {
        id: batchSettingsDialogLoader
        sourceComponent: Component {
            BatchSettingsDialog { onClosed: batchSettingsDialogLoader.release() }
        }
    }

    LazyDialogLoader {
        id: translationReviewDialogLoader
        sourceComponent: Component {
            TranslationReviewDialog { onClosed: translationReviewDialogLoader.release() }
        }
    }




    AppAlertDialog {
        id: appAlertDialog
    }

    ConfirmDialog {
        id: appConfirmationDialog
        property bool responseSent: false
        confirmText: qsTr("Xác nhận")
        onOpened: responseSent = false
        onConfirmed: {
            responseSent = true;
            AppController.respondToAppConfirmation(true);
        }
        onRejected: {
            if (!responseSent) {
                responseSent = true;
                AppController.respondToAppConfirmation(false);
            }
        }
    }

    DesktopNotificationBanner {
        id: desktopNotifier
        hostWindow: root
    }

    property string lastTrackedVideoId: ""
    property string lastTrackedVideoStatus: ""
    property int lastTrackedBatchCompleted: -1
    property string lastTrackedBatchKey: ""

    Connections {
        target: AppController
        function onProjectRenameRequested(key, name) {
            projectRenameDialogLoader.invoke("openForProject", [key, name]);
        }

        function onVideoDeleted() {
            if (!root.projectWorkspaceVisible) {
                root.pruneRouteHistory();
                return;
            }
            if (!AppController.hasOpenProject) {
                root.resetRouteHistory(root.workspaceReturnRoute);
                return;
            }
            root.replaceCurrentRoute(root.workspaceReturnRoute);
            root.pruneRouteHistory();
        }

        function onBatchDeleted() {
            if (!root.projectWorkspaceVisible) {
                root.pruneRouteHistory();
                return;
            }
            root.workspaceReturnRoute = root.routeBatchProjects;
            root.resetRouteHistory(root.routeBatchProjects);
        }

        function onProjectSetupChanged() {
            root.pruneRouteHistory();
        }

        function onSelectedVideoChanged() {
            root.pruneRouteHistory();
            const vid = AppController.selectedVideoId || "";
            const st = AppController.selectedStatus || "";
            if (vid.length > 0 && vid === root.lastTrackedVideoId && root.lastTrackedVideoStatus === "processing") {
                const clipName = AppController.selectedTitle || AppController.selectedFileName || qsTr("Video");
                if (st === "done") {
                    desktopNotifier.notify(qsTr("Aura Studio · Hoàn tất clip"), qsTr("Đã xử lý xong: %1").arg(clipName));
                } else if (st === "awaiting_review") {
                    desktopNotifier.notify(qsTr("Aura Studio · Cần duyệt bản dịch"), qsTr("Clip đã dịch xong, sẵn sàng duyệt: %1").arg(clipName));
                } else if (st === "failed") {
                    desktopNotifier.notify(qsTr("Aura Studio · Lỗi xử lý"), AppController.selectedFailureMessage || clipName);
                }
            }
            root.lastTrackedVideoId = vid;
            root.lastTrackedVideoStatus = st;
        }

        function onBatchChanged() {
            const bKey = AppController.openProjectKey || "";
            const doneCount = AppController.batchCompletedCount;
            const totalCount = AppController.batchCount;
            if (bKey.length > 0 && bKey === root.lastTrackedBatchKey && root.lastTrackedBatchCompleted >= 0 && doneCount > root.lastTrackedBatchCompleted) {
                if (doneCount >= totalCount && totalCount > 0) {
                    desktopNotifier.notify(qsTr("Aura Studio · Hoàn tất cả lô"), qsTr("Đã xử lý xong toàn bộ %1/%2 clip!").arg(doneCount).arg(totalCount));
                } else {
                    desktopNotifier.notify(qsTr("Aura Studio · Xong 1 clip trong lô"), qsTr("Tiến độ hàng loạt: %1/%2 clip hoàn tất.").arg(doneCount).arg(totalCount));
                }
            }
            root.lastTrackedBatchKey = bKey;
            root.lastTrackedBatchCompleted = doneCount;
        }

        function onSettingsChanged() {
            I18n.language = AppController.settingsLanguage;
        }

        function onAppAlertRequested(title, message, severity) {
            if (severity === "critical")
                appAlertDialog.showAlert(title, message, severity);
            else
                toastStack.show(title, message, severity, severity === "warning" ? 6200 : 4200);
        }

        function onAppConfirmationRequested(title, message) {
            appConfirmationDialog.title = title;
            appConfirmationDialog.message = message;
            appConfirmationDialog.open();
        }

        function onVideoExportCompleted(videoId, path) {
            toastStack.show(qsTr("Xuất video thành công"), path, "success", 6500);
            desktopNotifier.notify(qsTr("Aura Studio · Xuất video thành công"), path);
        }

        function onManualExportCompleted(kind, path) {
            desktopNotifier.notify(qsTr("Aura Studio · Xuất tệp hoàn tất"), path);
        }

        function onUrlImportFinished() {
            desktopNotifier.notify(qsTr("Aura Studio · Tải video hoàn tất"), qsTr("Clip từ liên kết đã được tải xong và sẵn sàng xử lý."));
        }

        function onApiKeySettingsRequested(provider) {
            root.navigate(root.routeApiKeys);
        }

        function onProjectPrepared() {
            const returnRoute = root.workspaceReturnRoute === root.routeHome || root.workspaceReturnRoute === root.routeProjects ? root.workspaceReturnRoute : "";
            if (AppController.projectType === "batch") {
                root.openProjectWorkspace(returnRoute || root.routeBatchProjects, root.routeBatchWorkspace);
            } else if (AppController.projectType === "manual") {
                root.openProjectWorkspace(returnRoute || root.routeManualProjects, root.routeManualWorkspace);
            } else {
                if (AppController.projectType === "download") {
                    root.openProjectWorkspace(returnRoute || root.routeDownloadProjects, root.routeDownloadWorkspace);
                } else if (AppController.projectType === "publish") {
                    root.openProjectWorkspace(returnRoute || root.routePublishProjects, root.routePublishWorkspace);
                } else {
                    root.openProjectWorkspace(returnRoute || root.routeSingleProjects, root.routeSingleWorkspace);
                }
            }
        }
    }

    Overlay.modal: Rectangle {
        color: Theme.scrim
        Behavior on opacity {
            NumberAnimation {
                duration: Theme.motionStandard
            }
        }
    }

    // Minimalist Apple monochrome artwork canvas behind transparent Liquid Glass panels
    Image {
        anchors.fill: parent
        source: Qt.resolvedUrl("../assets/branding/apple-wallpaper.png")
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        z: 0

        // Floating ambient liquid-mercury orb 1
        Rectangle {
            id: ambientOrb1
            width: 340
            height: 340
            radius: 170
            x: 120
            y: 80
            color: "transparent"
            border.width: 1
            border.color: "#1409090B"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#0A09090B" }
                GradientStop { position: 0.5; color: "#80FFFFFF" }
                GradientStop { position: 1.0; color: "#0509090B" }
            }
            SequentialAnimation on x {
                loops: Animation.Infinite
                running: Theme.motionEnabled
                NumberAnimation { from: 90; to: 360; duration: 9200; easing.type: Easing.InOutSine }
                NumberAnimation { from: 360; to: 90; duration: 9200; easing.type: Easing.InOutSine }
            }
            SequentialAnimation on y {
                loops: Animation.Infinite
                running: Theme.motionEnabled
                NumberAnimation { from: 60; to: 240; duration: 7600; easing.type: Easing.InOutSine }
                NumberAnimation { from: 240; to: 60; duration: 7600; easing.type: Easing.InOutSine }
            }
        }

        // Floating ambient liquid-mercury orb 2
        Rectangle {
            id: ambientOrb2
            width: 420
            height: 420
            radius: 210
            x: parent.width - 520
            y: parent.height - 460
            color: "transparent"
            border.width: 1
            border.color: "#1209090B"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#90FFFFFF" }
                GradientStop { position: 0.5; color: "#0809090B" }
                GradientStop { position: 1.0; color: "#60FFFFFF" }
            }
            SequentialAnimation on scale {
                loops: Animation.Infinite
                running: Theme.motionEnabled
                NumberAnimation { from: 0.92; to: 1.12; duration: 6400; easing.type: Easing.InOutSine }
                NumberAnimation { from: 1.12; to: 0.92; duration: 6400; easing.type: Easing.InOutSine }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12
        z: 1

        NavigationRail {
            visible: !root.projectWorkspaceVisible
            Layout.preferredWidth: root.compactNavigation ? Theme.navigationCompact : Theme.navigationExpanded
            Layout.fillHeight: true
            compact: root.compactNavigation
            currentSection: root.navigationSection()
            onSectionRequested: function (section) {
                AppController.refreshVideos();
                if (section === "single")
                    root.navigate(root.routeSingleProjects);
                else if (section === "manual")
                    root.navigate(root.routeManualProjects);
                else if (section === "batch")
                    root.navigate(root.routeBatchProjects);
                else if (section === "downloads")
                    root.navigate(root.routeDownloadProjects);
                else if (section === "social")
                    root.navigate(root.routePublishProjects);
                else if (section === "settings")
                    root.navigate(root.routeSettings);
                else
                    root.navigate(root.routeHome);
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            AppMenuBar {
                id: appMenuBar
                Layout.fillWidth: true
                Layout.preferredHeight: UiMetrics.toolbarHeight
                canGoBack: root.canNavigateBack
                canGoForward: root.canNavigateForward
                editAvailable: root.editScopeAvailable
                canUndo: AppController.canUndoEdit
                canRedo: AppController.canRedoEdit
                onBackRequested: root.navigateBack()
                onForwardRequested: root.navigateForward()
                onHomeRequested: root.navigate(root.routeHome)
                onUndoRequested: AppController.undoEdit()
                onRedoRequested: AppController.redoEdit()
                onNewSingleProjectRequested: {
                    root.workspaceReturnRoute = root.routeSingleProjects;
                    projectSetupDialogLoader.invoke("openForType", ["single"]);
                }
                onManualProjectRequested: {
                    root.workspaceReturnRoute = root.routeManualProjects;
                    projectSetupDialogLoader.invoke("openForType", ["manual"]);
                }
                onNewBatchProjectRequested: {
                    root.workspaceReturnRoute = root.routeBatchProjects;
                    projectSetupDialogLoader.invoke("openForType", ["batch"]);
                }
                onNewDownloadProjectRequested: {
                    root.workspaceReturnRoute = root.routeDownloadProjects;
                    projectSetupDialogLoader.invoke("openForType", ["download"]);
                }
                onNewPublishProjectRequested: {
                    root.workspaceReturnRoute = root.routePublishProjects;
                    projectSetupDialogLoader.invoke("openForType", ["publish"]);
                }
                onSettingsRequested: root.navigate(root.routeSettings)
                onApiKeysRequested: root.navigate(root.routeApiKeys)
                onPackagesRequested: root.navigate(root.routePackages)
            }

            RouteHost {
                id: routeHost
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentRoute: root.currentRoute

                onNewProjectRequested: function (projectType, returnRoute) {
                    root.workspaceReturnRoute = returnRoute;
                    projectSetupDialogLoader.invoke("openForType", [projectType]);
                }
                onWorkspaceRequested: function (returnRoute, workspaceRoute) {
                    root.openProjectWorkspace(returnRoute, workspaceRoute);
                }
                onNavigateRequested: function (route) {
                    AppController.refreshVideos();
                    root.navigate(route);
                }
                onReviewTranslationRequested: translationReviewDialogLoader.invoke("open", [])
                onUrlImportRequested: function (mode) {
                    urlImportDialogLoader.invoke("openForMode", [mode]);
                }
                onDownloadProjectImportRequested: function (mode) {
                    downloadProjectSourceDialogLoader.invoke("openForMode", [mode]);
                }
                onBatchSettingsRequested: batchSettingsDialogLoader.invoke("open", [])
            }

            ActivityTray {
                Layout.fillWidth: true
                showDetails: false
                activityState: root.selectedTaskFailed ? "failed"
                    : root.videoProcessing ? "processing"
                        : root.selectedTaskPaused ? "paused"
                        : root.selectedTaskQueued ? "queued" : "ready"
                message: root.selectedTaskFailed ? AppController.selectedFailureMessage
                    : root.videoProcessing ? (AppController.isSelectedVideoProcessing
                        ? AppController.selectedStageLabel
                        : qsTr("Đang xử lý video khác"))
                    : root.selectedTaskPaused || root.selectedTaskQueued
                        ? I18n.progressDetail(AppController.selectedProgressDetail) : ""
                progress: AppController.isSelectedVideoProcessing
                    && root.selectedProgressMeasured
                    && AppController.selectedStepId !== "waiting_for_models"
                    && AppController.selectedStepId !== "starting"
                    ? Math.max(0, Math.min(1, AppController.selectedProgress / 100))
                    : root.selectedTaskPaused
                        ? Math.max(0, Math.min(1, AppController.selectedProgress / 100)) : -1
            }
        }
    }

    Loader {
        id: modelSetupOverlayLoader
        anchors.fill: parent
        active: AppController.modelSetupVisible
        sourceComponent: Component {
            ModelSetupOverlay {}
        }
    }

    ToastStack {
        id: toastStack
        onDetailsRequested: (title, message, tone) => appAlertDialog.showAlert(title, message, tone)
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: Theme.space16 + (root.projectWorkspaceVisible ? UiMetrics.toolbarHeight : 40)
        anchors.rightMargin: Theme.space16
        width: Math.min(380, root.width - Theme.space32)
        z: 200
    }
}
