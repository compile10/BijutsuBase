/**
 * Global app state using Svelte 5 Runes
 */

let isSidebarOpen = $state(false);
let isUploadModalOpen = $state(false);
let isSearchModalOpen = $state(false);

// TODO: Change to use Context API. The risk is low for this since its UI but we should still do it.
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
		},
		get isSearchModalOpen() {
			return isSearchModalOpen;
		},
		set isSearchModalOpen(value: boolean) {
			isSearchModalOpen = value;
		}
	};
}

