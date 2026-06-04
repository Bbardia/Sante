// Global test setup, loaded once before any test file (see vite.config.ts `setupFiles`).
import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom does not implement matchMedia; Mantine reads it for color-scheme/media queries.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }) as unknown as MediaQueryList,
});

// jsdom lacks ResizeObserver; Mantine ScrollArea and Recharts need it.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverStub;

// jsdom does not implement scrollIntoView; Mantine Select calls it on the active option.
window.HTMLElement.prototype.scrollIntoView = vi.fn();
