<script lang="ts">
	import { getRecommendedTags } from '$lib/api';
	import { debounce } from '$lib/utils';
	import { fade } from 'svelte/transition';

	interface Props {
		value: string;
		placeholder?: string;
		inputClass?: string;
		class?: string; // For the wrapper
		onSubmit?: (e: Event) => void;
	}

	let { 
		value = $bindable(), 
		placeholder = 'Search...', 
		inputClass = '', 
		class: className = '',
		onSubmit 
	}: Props = $props();

	let suggestions = $state<string[]>([]);
	let showSuggestions = $state(false);
	let inputElement: HTMLInputElement;
	let suggestionIndex = $state(-1);

	// Get the word currently being typed (cursor position matters)
	function getCurrentWordInfo() {
		if (!inputElement) return null;
		
		const cursorPosition = inputElement.selectionStart || 0;
		const textBeforeCursor = value.slice(0, cursorPosition);
		const words = textBeforeCursor.split(/\s+/);
		const currentWord = words[words.length - 1];
		
		return {
			word: currentWord,
			startIndex: textBeforeCursor.lastIndexOf(currentWord),
			endIndex: cursorPosition
		};
	}

	const fetchSuggestions = debounce(async (query: string) => {
		if (!query || query.length < 1) {
			suggestions = [];
			showSuggestions = false;
			return;
		}

		try {
			suggestions = await getRecommendedTags(query, 10);
			showSuggestions = suggestions.length > 0;
			suggestionIndex = -1; // Reset selection
		} catch (err) {
			console.error('Failed to fetch suggestions:', err);
			suggestions = [];
			showSuggestions = false;
		}
	}, 200);

	function handleInput(event: Event) {
		const target = event.target as HTMLInputElement;
		value = target.value; // Update bound value manually just in case, though bind:value handles it

		const info = getCurrentWordInfo();
		if (info && info.word) {
			fetchSuggestions(info.word);
		} else {
			suggestions = [];
			showSuggestions = false;
		}
	}

	function selectSuggestion(tag: string) {
		if (!inputElement) return;

		const info = getCurrentWordInfo();
		if (info) {
			const beforeWord = value.slice(0, info.startIndex);
			const afterCursor = value.slice(info.endIndex);
			
			// Add tag and a space if one doesn't already exist
			const hasSpace = afterCursor.startsWith(' ');
			value = `${beforeWord}${tag}${hasSpace ? '' : ' '}${afterCursor}`;
			
			suggestions = [];
			showSuggestions = false;
			
			// Restore focus
			inputElement.focus();
			
			// Need to wait for DOM update before moving the cursor
			setTimeout(() => {
				const newCursorPos = info.startIndex + tag.length + 1;
				inputElement.setSelectionRange(newCursorPos, newCursorPos);
			}, 0);
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (!showSuggestions) return;

		if (event.key === 'ArrowDown') {
			event.preventDefault();
			if (suggestionIndex === suggestions.length - 1) {
				suggestionIndex = -1; // Wrap to search box
			} else {
				suggestionIndex += 1;
			}
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			if (suggestionIndex === -1) {
				suggestionIndex = suggestions.length - 1;
			} else {
				suggestionIndex -= 1;
			}
		} else if (event.key === 'Enter') {
			if (suggestionIndex >= 0 && suggestions[suggestionIndex]) {
				event.preventDefault();
				selectSuggestion(suggestions[suggestionIndex]);
			}
			// If no suggestion selected, let the form submit (default behavior) propagate
		} else if (event.key === 'Escape') {
			showSuggestions = false;
		}
	}

	function handleBlur() {
		// Small delay to allow click event on suggestion to fire
		setTimeout(() => {
			showSuggestions = false;
		}, 250);
	}
</script>

<div class="relative {className}">
	<input
		bind:this={inputElement}
		type="text"
		{value}
		oninput={handleInput}
		onkeydown={handleKeydown}
		onblur={handleBlur}
		{placeholder}
		class={inputClass}
		autocomplete="off"
	/>

	{#if showSuggestions}
		<div
			transition:fade={{ duration: 100 }}
			class="absolute left-0 right-0 top-full z-50 mt-1 max-h-60 overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800"
		>
			{#each suggestions as tag, index}
				<button
					type="button"
					class="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700
					{index === suggestionIndex ? 'bg-gray-100 dark:bg-gray-700' : ''}"
					onclick={() => selectSuggestion(tag)}
				>
					{tag}
				</button>
			{/each}
		</div>
	{/if}
</div>

