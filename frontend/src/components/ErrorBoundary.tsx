import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, message: '' };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message || 'Unexpected rendering error.' };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="m-6 rounded-2xl border border-red-800 bg-red-950/30 p-6 text-red-100">
          <h2 className="text-lg font-semibold">This view could not be rendered.</h2>
          <p className="mt-2 text-sm text-red-200">{this.state.message}</p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, message: '' })}
            className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold hover:bg-red-600"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
