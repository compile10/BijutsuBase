<script lang="ts">
	import CalendarIcon from '~icons/mdi/calendar';
	import FileSizeIcon from '~icons/mdi/file-document-outline';
	import ChevronDown from '~icons/mdi/chevron-down';
	import ArrowUp from '~icons/mdi/arrow-up';
	import ArrowDown from '~icons/mdi/arrow-down';
	import Check from '~icons/mdi/check';

	let { value = $bindable(), onchange, class: className = '' } = $props<{
		value: string;
		onchange?: () => void;
		class?: string;
	}>();

	let isOpen = $state(false);
	let container: HTMLElement;

	const optionGroups = [
		{
			title: 'Date',
			icon: CalendarIcon,
			options: [
				{ label: 'Newest', value: 'date_desc', icon: ArrowDown },
				{ label: 'Oldest', value: 'date_asc', icon: ArrowUp }
			]
		},
		{
			title: 'Size',
			icon: FileSizeIcon,
			options: [
				{ label: 'Largest', value: 'size_desc', icon: ArrowDown },
				{ label: 'Smallest', value: 'size_asc', icon: ArrowUp }
			]
		}
	];

	function select(optionValue: string) {
		if (value === optionValue) return;
		
		value = optionValue;
		isOpen = false;
		onchange?.();
	}

	function handleClickOutside(event: MouseEvent) {
		if (container && !container.contains(event.target as Node)) {
			isOpen = false;
		}
	}

	function getLabel(val: string): string {
		const allOptions = optionGroups.flatMap((group) => group.options);
		return allOptions.find((o) => o.value === val)?.label ?? 'Sort';
	}

	$effect(() => {
		if (isOpen) {
			window.addEventListener('click', handleClickOutside);
		} else {
			window.removeEventListener('click', handleClickOutside);
		}
		return () => {
			window.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<div class="relative" bind:this={container}>
	<button
		onclick={(e) => {
            e.stopPropagation(); 
            isOpen = !isOpen;
        }}
		class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 hover:bg-gray-50 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 dark:focus:border-primary-400 dark:focus:ring-primary-400 {className}"
		type="button"
	>
		<span class="flex items-center gap-2">
			{#if value.startsWith('date')}
				<CalendarIcon class="text-gray-500 dark:text-gray-400" />
			{:else}
				<FileSizeIcon class="text-gray-500 dark:text-gray-400" />
			{/if}
			<span>{getLabel(value)}</span>
		</span>
		<ChevronDown
			class="h-4 w-4 text-gray-500 transition-transform duration-200 dark:text-gray-400 {isOpen
				? 'rotate-180'
				: ''}"
		/>
	</button>

	{#if isOpen}
		<div
			class="absolute right-0 top-full z-50 mt-2 w-56 origin-top-right rounded-lg border border-gray-200 bg-white py-2 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none dark:border-gray-700 dark:bg-gray-800"
		>
			{#each optionGroups as group, groupIndex}
				{#if groupIndex > 0}
					<div class="my-1 border-t border-gray-200 dark:border-gray-700"></div>
				{/if}

				<!-- Group Header -->
				<div class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
					<div class="flex items-center gap-2">
						<group.icon />
						<span>{group.title}</span>
					</div>
				</div>

				<!-- Group Options -->
				{#each group.options as option}
					<button
						onclick={() => select(option.value)}
						class="flex w-full items-center justify-between px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 {value ===
						option.value
							? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
							: 'text-gray-700 dark:text-gray-200'}"
					>
						<span class="flex items-center gap-2">
							<option.icon class="h-4 w-4 opacity-70" />
							{option.label}
						</span>
						{#if value === option.value}
							<Check class="h-4 w-4 text-primary-600 dark:text-primary-400" />
						{/if}
					</button>
				{/each}
			{/each}
		</div>
	{/if}
</div>

