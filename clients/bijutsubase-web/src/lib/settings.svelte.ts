/**
 * Settings context for BijutsuBase
 * 
 * Uses Svelte's context API to provide SSR-safe global settings.
 * Settings are persisted to localStorage on the client side.
 */

import { setContext, getContext } from 'svelte';

const SETTINGS_KEY = Symbol('app-settings');

export type MaxRating = 'safe' | 'sensitive' | 'questionable' | 'explicit' | null;

export interface SettingsContext {
	readonly maxRating: MaxRating;
	setMaxRating: (value: MaxRating) => void;
}

/**
 * Create and initialize the settings context.
 * Should be called once in the root layout.
 */
export function createSettingsContext(): SettingsContext {
	let maxRating = $state<MaxRating>(null);

	// Load from localStorage on client only
	if (typeof window !== 'undefined') {
		try {
			const saved = localStorage.getItem('bijutsubase-settings');
			if (saved) {
				const parsed = JSON.parse(saved);
				maxRating = parsed.maxRating ?? null;
			}
		} catch (error) {
			console.error('Failed to load settings from localStorage:', error);
		}
	}

	const context: SettingsContext = {
		get maxRating() {
			return maxRating;
		},
		setMaxRating(value: MaxRating) {
			maxRating = value;
			// Persist to localStorage on client only
			if (typeof window !== 'undefined') {
				try {
					localStorage.setItem(
						'bijutsubase-settings',
						JSON.stringify({ maxRating: value })
					);
				} catch (error) {
					console.error('Failed to save settings to localStorage:', error);
				}
			}
		}
	};

	setContext(SETTINGS_KEY, context);
	return context;
}

/**
 * Get the settings context.
 * Must be called from a component that is a child of the component that called createSettingsContext.
 */
export function getSettingsContext(): SettingsContext {
	return getContext<SettingsContext>(SETTINGS_KEY);
}
