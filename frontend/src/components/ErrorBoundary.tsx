import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI error', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="fm-card" style={{ margin: 16, textAlign: 'center' }}>
          <h2>Что-то пошло не так</h2>
          <p style={{ color: 'var(--text-secondary)' }}>
            Произошла ошибка интерфейса. Обновите страницу — данные не потеряются.
          </p>
          <button className="fm-btn" onClick={() => window.location.reload()}>
            Обновить
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
