<script lang="ts">
	import WindowModal from './WindowModal.svelte';
	import IconImageOff from '~icons/mdi/image-off-outline';

	let {
		isOpen = $bindable(false),
		message = 'This image could not be found on Danbooru, so its tags were left unchanged.'
	} = $props<{
		isOpen: boolean;
		message?: string;
	}>();
</script>

<WindowModal bind:isOpen title="Image Not Found" maxWidth="max-w-md">
	<div class="p-6">
		<div class="mb-6 flex flex-col items-center text-center">
			<div class="mb-4 rounded-full bg-yellow-100 p-3 dark:bg-yellow-900/30">
				<IconImageOff class="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
			</div>
			<h3 class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">Image Not Found</h3>
			<p class="text-gray-500 dark:text-gray-400">{message}</p>
		</div>

		<div class="flex justify-end">
			<button
				onclick={() => (isOpen = false)}
				class="rounded-lg bg-primary-600 px-4 py-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-600"
			>
				Close
			</button>
		</div>
	</div>
</WindowModal>
