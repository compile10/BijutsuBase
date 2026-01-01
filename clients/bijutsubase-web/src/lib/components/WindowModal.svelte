<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import type { Snippet } from 'svelte';

	let {
		isOpen = $bindable(false),
		title = '',
		maxWidth = 'max-w-2xl',
		onClose,
		children
	} = $props<{
		isOpen?: boolean;
		title?: string;
		maxWidth?: string;
		onClose?: () => void;
		children: Snippet;
	}>();

	function handleClose() {
		if (onClose) {
			onClose();
		} else {
			isOpen = false;
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		}
	}

	$effect(() => {
		if (isOpen && typeof window !== 'undefined') {
			const originalOverflow = document.body.style.overflow;
			document.body.style.overflow = 'hidden';
			window.addEventListener('keydown', handleKeydown);

			return () => {
				window.removeEventListener('keydown', handleKeydown);
				document.body.style.overflow = originalOverflow;
			};
		}
	});
</script>

{#if isOpen}
	<div
		class="fixed inset-0 z-60 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
		transition:fade={{ duration: 200 }}
		onclick={handleClose}
		role="presentation"
	>
		<div
			class="relative flex max-h-[90vh] w-full flex-col rounded-xl bg-white shadow-xl dark:bg-gray-800 {maxWidth}"
			transition:fly={{ y: 20, duration: 200 }}
			onclick={(e) => e.stopPropagation()}
			onkeydown={() => {}}
			role="dialog"
			aria-modal="true"
			aria-label={title}
			tabindex="-1"
		>
			{@render children()}
		</div>
	</div>
{/if}

