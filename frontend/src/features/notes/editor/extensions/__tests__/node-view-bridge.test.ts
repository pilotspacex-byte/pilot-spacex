/**
 * node-view-bridge utility tests
 *
 * Tests the createNodeViewBridgeContext factory used to pass data from plain
 * NodeView roots to MobX observer() children without wrapping the root in observer().
 *
 * RED phase: node-view-bridge.ts does not exist yet (Plan 03 creates it).
 */
import { describe, it, expect } from 'vitest';
import React from 'react';
import { renderHook } from '@testing-library/react';
import { createNodeViewBridgeContext } from '../node-view-bridge';

describe('createNodeViewBridgeContext', () => {
  it('test_factory_returns_provider_and_useBridgeContext', () => {
    const bridge = createNodeViewBridgeContext<{ value: string }>();
    expect(bridge).toHaveProperty('Provider');
    expect(bridge).toHaveProperty('useBridgeContext');
    expect(typeof bridge.useBridgeContext).toBe('function');
  });

  it('test_useBridgeContext_throws_outside_provider', () => {
    const bridge = createNodeViewBridgeContext<{ count: number }>();

    // Suppress expected React error boundary output
    const originalError = console.error;
    console.error = () => {};

    expect(() => {
      renderHook(() => bridge.useBridgeContext());
    }).toThrow('NodeView bridge context used outside provider');

    console.error = originalError;
  });

  it('test_useBridgeContext_returns_value_inside_provider', () => {
    const bridge = createNodeViewBridgeContext<{ label: string }>();
    const testValue = { label: 'hello' };

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(bridge.Provider, { value: testValue }, children);

    const { result } = renderHook(() => bridge.useBridgeContext(), { wrapper });
    expect(result.current).toEqual(testValue);
    expect(result.current.label).toBe('hello');
  });

  it('test_multiple_independent_bridge_contexts_do_not_cross_contaminate', () => {
    const bridgeA = createNodeViewBridgeContext<{ a: number }>();
    const bridgeB = createNodeViewBridgeContext<{ b: string }>();

    const wrapperA = ({ children }: { children: React.ReactNode }) =>
      React.createElement(bridgeA.Provider, { value: { a: 42 } }, children);

    const { result: resultA } = renderHook(() => bridgeA.useBridgeContext(), { wrapper: wrapperA });
    expect(resultA.current.a).toBe(42);

    // bridgeB has no provider — should throw
    expect(() => {
      renderHook(() => bridgeB.useBridgeContext());
    }).toThrow('NodeView bridge context used outside provider');
  });
});
