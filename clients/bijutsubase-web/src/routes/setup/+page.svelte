<script lang="ts">
	import { goto } from '$app/navigation';
	import { createAdminAccount, login } from '$lib/api';
	import { getAuthContext } from '$lib/auth.svelte';
	import IconKey from '~icons/mdi/key';

	const authState = getAuthContext();

	let username = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let error = $state('');

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = '';

		// Validation
		if (!username.trim()) {
			error = 'Username is required';
			return;
		}

		if (username.trim().length < 3) {
			error = 'Username must be at least 3 characters';
			return;
		}

		if (username.trim().length > 50) {
			error = 'Username must be at most 50 characters';
			return;
		}

		if (!email.trim()) {
			error = 'Email is required';
			return;
		}

		if (!password) {
			error = 'Password is required';
			return;
		}

		if (password.length < 8) {
			error = 'Password must be at least 8 characters';
			return;
		}

		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}

		isLoading = true;

		try {
			await createAdminAccount(email.trim(), password, username.trim());
			authState.needsSetup = false;
			// Automatically log in with the newly created account
			await login(email.trim(), password);
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create admin account';
		} finally {
			isLoading = false;
		}
	}

	// Redirect if setup is not needed
	$effect(() => {
		if (!authState.isLoading && !authState.needsSetup) {
			goto('/');
		}
	});
</script>

<svelte:head>
	<title>Setup - BijutsuBase</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-10 dark:bg-gray-900">
	<div class="w-full max-w-md">
		<!-- Logo and Title -->
		<div class="mb-8 text-center">
			<div
				class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-600/10 ring-1 ring-primary-600/30 dark:bg-primary-500/10 dark:ring-primary-500/30"
			>
				<IconKey class="h-8 w-8 text-primary-600 dark:text-primary-400" />
			</div>
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white">Welcome to BijutsuBase</h1>
			<p class="mt-2 text-gray-600 dark:text-gray-400">Create your admin account to get started</p>
		</div>

		<!-- Setup Form -->
		<div class="rounded-2xl bg-white p-8 shadow-xl ring-1 ring-black/5 dark:bg-gray-800 dark:ring-white/10">
			<form onsubmit={handleSubmit} class="space-y-6">
				{#if error}
					<div
						class="rounded-lg bg-red-50 p-4 text-center text-sm text-red-700 ring-1 ring-red-200 dark:bg-red-500/10 dark:text-red-200 dark:ring-red-500/20"
					>
						{error}
					</div>
				{/if}

				<div>
					<label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-200">
						Username
					</label>
					<input
						type="text"
						id="username"
						bind:value={username}
						required
						autocomplete="username"
						class="mt-2 block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-500 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
						placeholder="Choose a username"
					/>
				</div>

				<div>
					<label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-200">
						Email Address
					</label>
					<input
						type="email"
						id="email"
						bind:value={email}
						required
						autocomplete="email"
						class="mt-2 block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-500 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
						placeholder="admin@example.com"
					/>
				</div>

				<div>
					<label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-200">
						Password
					</label>
					<input
						type="password"
						id="password"
						bind:value={password}
						required
						autocomplete="new-password"
						class="mt-2 block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-500 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
						placeholder="At least 8 characters"
					/>
				</div>

				<div>
					<label for="confirmPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-200">
						Confirm Password
					</label>
					<input
						type="password"
						id="confirmPassword"
						bind:value={confirmPassword}
						required
						autocomplete="new-password"
						class="mt-2 block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-500 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
						placeholder="Repeat your password"
					/>
				</div>

				<button
					type="submit"
					disabled={isLoading}
					class="w-full rounded-lg bg-primary-600 px-4 py-3 font-semibold text-white transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600 dark:focus:ring-primary-400 dark:focus:ring-offset-gray-900"
				>
					{isLoading ? 'Creating Account...' : 'Create Admin Account'}
				</button>
			</form>
		</div>

		<p class="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
			This account will have full administrative privileges
		</p>
	</div>
</div>
