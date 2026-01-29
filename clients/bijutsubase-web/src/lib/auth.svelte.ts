/**
 * Authentication state management using Svelte 5 Runes with Context API
 * 
 * This module provides SSR-safe auth state by using Svelte's context API.
 * The auth state is created per-request and attached to the component tree,
 * preventing state leakage between users during server-side rendering.
 * 
 * Authentication is handled via HttpOnly cookies set by the server,
 * so no token storage is needed in the frontend.
 */

import { setContext, getContext } from 'svelte';

export interface User {
	id: string;
	email: string;
	username: string;
	avatar: string | null;
	is_active: boolean;
	is_superuser: boolean;
	is_verified: boolean;
}

export interface SetupStatus {
	needs_setup: boolean;
}

export interface AuthState {
	user: User | null;
	isLoading: boolean;
	needsSetup: boolean;
	readonly isAuthenticated: boolean;
}

// Context key for auth state
const AUTH_CONTEXT_KEY = Symbol('auth');

// Reference to current auth state (for use by api.ts functions)
let currentAuthState: AuthState | null = null;

/**
 * Create the auth context and provide it to child components.
 * Call this in the root +layout.svelte.
 */
export function createAuthContext(): AuthState {
	// Create reactive state with computed isAuthenticated
	// With cookie-based auth, we determine authentication by whether we have a user object
	const authState: AuthState = $state({
		user: null as User | null,
		isLoading: true,
		needsSetup: false,
		get isAuthenticated() {
			return this.user !== null;
		}
	});

	// Store reference for api.ts functions
	currentAuthState = authState;

	// Set context for child components
	setContext(AUTH_CONTEXT_KEY, authState);

	return authState;
}

/**
 * Get the auth state from context.
 * Call this in any component that needs access to auth state.
 */
export function getAuthContext(): AuthState {
	const context = getContext<AuthState | undefined>(AUTH_CONTEXT_KEY);
	if (!context) {
		throw new Error(
			'Auth context not found. Make sure createAuthContext() is called in a parent layout.'
		);
	}
	return context;
}

/**
 * Clear the current user state (used on logout).
 * The actual cookie is cleared by the server on logout.
 */
export function clearUser() {
	if (currentAuthState) {
		currentAuthState.user = null;
	}
}

/**
 * Set the current user.
 */
export function setUser(newUser: User | null) {
	if (currentAuthState) {
		currentAuthState.user = newUser;
	}
}

/**
 * Set loading state.
 */
export function setLoading(loading: boolean) {
	if (currentAuthState) {
		currentAuthState.isLoading = loading;
	}
}

/**
 * Set needs setup state.
 */
export function setNeedsSetup(needs: boolean) {
	if (currentAuthState) {
		currentAuthState.needsSetup = needs;
	}
}
