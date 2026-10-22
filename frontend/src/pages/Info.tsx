export default function Info() {
  return (
    <div className="fm-rise">
      <div className="fm-card">
        <h3>🧵 Пересчёт для полукреста</h3>
        <div style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginTop: 6 }}>
          Вышиваете полукрестом? Норма пересчитывается ×1,5:
        </div>
        <div style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginTop: 6 }}>
          500 крестиков = 750 полукрестов<br />
          400 крестиков = 600 полукрестов<br />
          300 крестика = 450 полукрестов
        </div>
      </div>
      <div className="fm-card" style={{ marginTop: 12 }}>
        <h3>🔑 Кодовое слово</h3>
        <div style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginTop: 6 }}>
          Кодовое слово — название карточки
        </div>
      </div>
    </div>
  );
}
