import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

// Simple component for testing the test setup
function TestComponent({ message }: { message: string }) {
  return <div data-testid="test-component">{message}</div>;
}

describe('Test Setup', () => {
  it('should render a component', () => {
    render(<TestComponent message="Hello, Pilot Space!" />);

    const element = screen.getByTestId('test-component');
    expect(element).toBeInTheDocument();
    expect(element).toHaveTextContent('Hello, Pilot Space!');
  });

  it('should support snapshot testing', () => {
    const { container } = render(<TestComponent message="Snapshot test" />);
    expect(container).toMatchSnapshot();
  });
});
