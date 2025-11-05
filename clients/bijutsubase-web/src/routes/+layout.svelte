<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import UploadModal from '$lib/components/UploadModal.svelte';
	import IconUpload from '~icons/mdi/image-plus';

	let { children } = $props();
	let isUploadModalOpen = $state(false);
</script>

<svelte:head>
	<title>BijutsuBase</title>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="min-h-screen bg-white dark:bg-zinc-950 text-gray-900 dark:text-gray-100">
	<!-- Global Upload Button - fixed top right -->
	<button
		onclick={() => (isUploadModalOpen = true)}
		class="fixed right-4 top-4 z-40 rounded-full bg-indigo-600 p-1.5 text-white shadow-lg transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 sm:p-2 md:p-2 dark:bg-indigo-500 dark:hover:bg-indigo-600"
		aria-label="Upload file"
	>
		<IconUpload class="h-4 w-4 sm:h-5 sm:w-5 md:h-6 md:w-6" />
	</button>

	<!-- Upload Modal -->
	<UploadModal bind:isOpen={isUploadModalOpen} />

	{@render children()}
</div>
