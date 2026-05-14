// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces

interface D1PreparedStatement {
	bind(...values: unknown[]): D1PreparedStatement;
	first<T = unknown>(column?: string): Promise<T | null>;
	all<T = unknown>(): Promise<{ results: T[]; success: boolean }>;
	run(): Promise<{ success: boolean }>;
}
interface D1Database {
	prepare(query: string): D1PreparedStatement;
}

declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		interface Platform {
			env?: {
				DB?: D1Database;
				ASSETS?: Fetcher;
			};
		}
	}
}

export {};
