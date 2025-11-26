<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import UploadModal from '$lib/components/UploadModal.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import IconUpload from '~icons/mdi/image-plus';
	import IconMenu from '~icons/mdi/menu';

	let { children } = $props();
	let isUploadModalOpen = $state(false);
	let isSidebarOpen = $state(false);
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="min-h-screen">
	<!-- Global Menu Button - fixed top left -->
	<button
		onclick={() => (isSidebarOpen = true)}
		class="fixed left-4 top-4 z-40 p-1.5 text-gray-700 transition-transform hover:scale-110 focus:outline-none sm:p-2 md:p-2 dark:text-gray-200"
		aria-label="Open menu"
	>
		<IconMenu class="h-6 w-6 shadow-sm" />
	</button>

	<!-- Global Upload Button - fixed top right -->
	<button
		onclick={() => (isUploadModalOpen = true)}
		class="fixed right-4 top-4 z-40 rounded-full bg-primary-600 p-1.5 text-white shadow-lg transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:p-2 md:p-2 dark:bg-primary-500 dark:hover:bg-primary-600"
		aria-label="Upload file"
	>
		<IconUpload class="h-4 w-4 sm:h-5 sm:w-5 md:h-6 md:w-6" />
	</button>

	<!-- Sidebar -->
	<Sidebar bind:isOpen={isSidebarOpen} />

	<!-- Upload Modal -->
	<UploadModal bind:isOpen={isUploadModalOpen} />

	{@render children()}
</div>
