<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';
	import IconSearch from '~icons/mdi/magnify';
	import IconClock from '~icons/mdi/clock-outline';
	import IconFolderMultiple from '~icons/mdi/folder-multiple-outline';

	let { isOpen = $bindable(false) } = $props();

	const quotes = [
		'The purpose of art is washing the dust of daily life off our souls.',
		'Art is not what you see, but what you make others see.',
		'To practice any art, no matter how well or badly, is a way to make your soul grow.',
		'Time is passing so quickly. Right now, I feel like complaining to Einstein. Whether time is slow or fast depends on perception. Relativity theory is so romantic. And so sad.',
		'Things that don\'t change go extinct.',
		'I dreamt I was a butterfly. I couldn\'t tell I was dreaming. But when I woke, I was I and not a butterfly. Was I dreaming that I was the butterfly, or was the butterfly dreaming that it was me?',
		'If people refuse to accept you, I\'ll just accept you even more.',
		'The fake is of far greater value. In its deliberate attempt to be real, it\'s more real than the real thing.',
	];

	let currentQuote = $state('');

	$effect(() => {
		if (isOpen) {
			currentQuote = quotes[Math.floor(Math.random() * quotes.length)];
		}
	});

	function close() {
		isOpen = false;
	}
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
		transition:fade={{ duration: 200 }}
		onclick={close}
		role="button"
		tabindex="0"
		onkeydown={(e) => {
			if (e.key === 'Escape') close();
		}}
		aria-label="Close menu"
	></div>

	<!-- Sidebar -->
	<aside
		class="fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg dark:bg-gray-900"
		transition:fly={{ x: -200, duration: 300 }}
	>
		<div class="flex h-full flex-col">
			<!-- Header -->
			<div
				class="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-800"
			>
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white">BijutsuBase</h2>
				<button
					onclick={close}
					class="rounded-lg p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
					aria-label="Close menu"
				>
					<IconClose class="h-6 w-6" />
				</button>
			</div>

			<!-- Navigation -->
			<nav class="flex-1 overflow-y-auto p-4">
				<ul class="space-y-2">
					<li>
						<a
							href="/latest"
							class="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
							onclick={close}
						>
							<IconClock class="h-5 w-5" />
							<span>Latest</span>
						</a>
					</li>
					<li>
						<a
							href="/pools"
							class="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
							onclick={close}
						>
							<IconFolderMultiple class="h-5 w-5" />
							<span>Pools</span>
						</a>
					</li>
				</ul>
			</nav>

			<!-- Footer -->
			<div
				class="border-t border-gray-200 p-6 text-center text-xs italic text-gray-500 dark:border-gray-800 dark:text-gray-400"
			>
				"{currentQuote}"
			</div>
		</div>
	</aside>
{/if}
