<script lang="ts">
	import type { FileResponse, TagResponse } from '$lib/api';
	import { associateTag, dissociateTag } from '$lib/api';
	import IconClose from '~icons/mdi/close';
	import IconAccount from '~icons/mdi/account';
	import IconPalette from '~icons/mdi/palette';
	import IconCopyright from '~icons/mdi/copyright';
	import IconTag from '~icons/mdi/tag';
	import IconInformation from '~icons/mdi/information-outline';
	import IconPlus from '~icons/mdi/plus';

	let { 
		file = $bindable<FileResponse | undefined>(undefined),
		tags: providedTags = undefined,
		onAddTag = undefined,
		onDeleteTag = undefined,
		disabled = false
	} = $props<{ 
		file?: FileResponse,
		tags?: TagResponse[],
		onAddTag?: (name: string, category: string) => Promise<void>,
		onDeleteTag?: (name: string) => Promise<void>,
		disabled?: boolean
	}>();

	// Tag editing state
	let isEditingTags = $state(false);
	let newTagCategory = $state('general');
	let newTagName = $state('');
	let tagBusy = $state(false);
	let tagError = $state<string | null>(null);

	// Determine which tags to display: provided tags (bulk edit) or file tags
	let displayTags = $derived(providedTags ?? file?.tags ?? []);

	// Category order for tabs
	const categoryOrder = ['character', 'artist', 'copyright', 'general', 'meta'];

	// Group tags by category
	let tagsByCategory = $derived.by(() => {
		const groups: Record<string, TagResponse[]> = {};
		for (const tag of displayTags) {
			if (!groups[tag.category]) {
				groups[tag.category] = [];
			}
			groups[tag.category].push(tag);
		}
		return groups;
	});

	// Get available categories in order
	let availableCategories = $derived(
		categoryOrder.filter((cat) => tagsByCategory[cat]?.length > 0)
	);

	// Capitalize first letter
	function capitalize(str: string): string {
		return str.charAt(0).toUpperCase() + str.slice(1);
	}

	// Get icon component for category
	function getCategoryIcon(category: string) {
		switch (category) {
			case 'character':
				return IconAccount;
			case 'artist':
				return IconPalette;
			case 'copyright':
				return IconCopyright;
			case 'general':
				return IconTag;
			case 'meta':
				return IconInformation;
			default:
				return IconTag;
		}
	}

	// Get color classes for category
	function getCategoryColorClasses(category: string): string {
		switch (category) {
			case 'character':
				return 'border-l-green-500';
			case 'artist':
				return 'border-l-red-500';
			case 'copyright':
				return 'border-l-violet-500';
			case 'general':
				return 'border-l-blue-500';
			case 'meta':
				return 'border-l-yellow-300';
			default:
				return 'border-l-gray-500';
		}
	}

	// Handle tag click - open search in new tab
	function handleTagClick(tagName: string) {
		const url = `/search?tags=${encodeURIComponent(tagName)}`;
		window.open(url, '_blank');
	}

	// Add a new tag
	async function handleAddTag() {
		const trimmedName = newTagName.trim();
		if (!trimmedName) {
			tagError = 'Tag name cannot be empty';
			return;
		}

		tagBusy = true;
		tagError = null;

		try {
			if (onAddTag) {
				await onAddTag(trimmedName, newTagCategory);
			} else if (file) {
				const updatedFile = await associateTag({
					file_sha256: file.sha256_hash,
					tag_name: trimmedName,
					category: newTagCategory
				});
				file = updatedFile;
			}
			
			newTagName = '';
			isEditingTags = false;
		} catch (err) {
			tagError = err instanceof Error ? err.message : 'Failed to add tag(s)';
		} finally {
			tagBusy = false;
		}
	}

	// Delete a tag
	async function handleDeleteTag(tagName: string) {
		tagBusy = true;
		tagError = null;

		try {
			if (onDeleteTag) {
				await onDeleteTag(tagName);
			} else if (file) {
				const updatedFile = await dissociateTag({
					file_sha256: file.sha256_hash,
					tag_name: tagName
				});
				file = updatedFile;
			}
		} catch (err) {
			tagError = err instanceof Error ? err.message : 'Failed to delete tag(s)';
		} finally {
			tagBusy = false;
		}
	}
</script>

<section class="mb-6">
	<div class="mb-3 flex items-center justify-between">
		<h4 class="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">Tags</h4>
		<button
			onclick={() => (isEditingTags = !isEditingTags)}
			disabled={tagBusy || disabled}
			class="flex items-center gap-1 rounded-lg bg-primary-600 px-2 py-1 text-xs font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
			aria-label="Add tag"
		>
			<IconPlus class="h-4 w-4" />
			Add Tag
		</button>
	</div>

	<!-- Tag Error Message -->
	{#if tagError}
		<div class="mb-3 rounded-lg border border-red-300 bg-red-50 p-2 dark:border-red-800 dark:bg-red-900/20">
			<p class="text-xs text-red-800 dark:text-red-400">{tagError}</p>
		</div>
	{/if}

	<!-- Add Tag Form -->
	{#if isEditingTags}
		<div class="mb-3 rounded-lg border border-gray-300 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/50">
			<div class="space-y-2">
				<div>
					<label for="tag-name" class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
						Tag Name
					</label>
					<input
						id="tag-name"
						type="text"
						bind:value={newTagName}
						disabled={tagBusy || disabled}
						placeholder="Enter tag name..."
						class="w-full rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500"
						onkeydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								handleAddTag();
							}
						}}
					/>
				</div>
				<div>
					<label for="tag-category" class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
						Category
					</label>
					<select
						id="tag-category"
						bind:value={newTagCategory}
						disabled={tagBusy || disabled}
						class="w-full rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					>
						<option value="general">General</option>
						<option value="artist">Artist</option>
						<option value="copyright">Copyright</option>
						<option value="character">Character</option>
						<option value="meta">Meta</option>
					</select>
				</div>
				<div class="flex justify-end gap-2">
					<button
						onclick={() => {
							isEditingTags = false;
							newTagName = '';
							tagError = null;
						}}
						disabled={tagBusy || disabled}
						class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
					>
						Cancel
					</button>
					<button
						onclick={handleAddTag}
						disabled={tagBusy || disabled || !newTagName.trim()}
						class="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
					>
						{tagBusy ? 'Adding...' : 'Add'}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- All Categories Displayed -->
	{#if displayTags.length > 0}
		<div class="space-y-3">
			{#each availableCategories as category (category)}
				{@const Icon = getCategoryIcon(category)}
				<div class="rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-100 dark:bg-gray-800/50 p-3">
					<!-- Category Header -->
					<div class="mb-2 flex items-center gap-2">
						<Icon class="h-4 w-4 text-gray-600 dark:text-gray-400" />
						<span class="text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-300">
							{capitalize(category)}
						</span>
						<span class="text-xs text-gray-500 dark:text-gray-500">
							({tagsByCategory[category].length})
						</span>
					</div>
					
					<!-- Tags for this Category -->
					<div class="flex flex-wrap gap-2">
						{#each tagsByCategory[category] as tag (tag.name)}
							<div class="group relative inline-flex items-center rounded-full border-l-4 bg-gray-200 dark:bg-gray-700 px-2.5 py-1 text-xs text-gray-800 dark:text-gray-200 transition-colors hover:bg-gray-300 dark:hover:bg-gray-600 {getCategoryColorClasses(category)}">
								<button
									onclick={() => handleTagClick(tag.name)}
									class="hover:text-gray-900 dark:hover:text-white focus:outline-none"
									title="Click to search for this tag"
								>
									{tag.name}
								</button>
								<button
									onclick={(e) => {
										e.stopPropagation();
										handleDeleteTag(tag.name);
									}}
									disabled={tagBusy || disabled}
									class="ml-1.5 rounded-full p-0.5 text-gray-600 hover:bg-red-100 hover:text-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:cursor-not-allowed disabled:opacity-50 dark:text-gray-400 dark:hover:bg-red-900 dark:hover:text-red-300"
									title="Remove tag"
									aria-label="Remove tag {tag.name}"
								>
									<IconClose class="h-3 w-3" />
								</button>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<p class="text-sm text-gray-500 dark:text-gray-400">No tags yet</p>
	{/if}
</section>
