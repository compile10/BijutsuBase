/**
 * Global app state using Svelte 5 Runes
 */

let isSidebarOpen = $state(false);
let isUploadModalOpen = $state(false);

export function getAppState() {
	return {
		get isSidebarOpen() {
			return isSidebarOpen;
		},
		set isSidebarOpen(value: boolean) {
			isSidebarOpen = value;
		},
		get isUploadModalOpen() {
			return isUploadModalOpen;
		},
		set isUploadModalOpen(value: boolean) {
			isUploadModalOpen = value;
		}
	};
}

