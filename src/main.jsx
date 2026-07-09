import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createClient } from '@supabase/supabase-js';
import './styles.css';

const MEMBERS = [
  { key: 'nakamura', name: '中村' },
  { key: 'kurihara', name: '栗原' },
  { key: 'yushi', name: 'ゆーし' },
  { key: 'kuronuma', name: '黒沼' },
  { key: 'inoue', name: '井上' },
  { key: 'manji', name: 'まんじ' },
  { key: 'manji_friend', name: 'まんじ友達' },
  { key: 'lee', name: 'リー' },
  { key: 'taniyone', name: '谷米' }
];

const RENTAL_ITEMS = [
  { key: 'full_set', label: 'フルセット', fullLabel: 'レンタルタックル（フルセット）' },
  { key: 'bishi', label: 'ビシのみ', fullLabel: 'ビシのみ' },
  { key: 'iwashi', label: 'イワシ', fullLabel: 'イワシ' },
  { key: 'rod_holder', label: 'ロッドホルダーだけ', fullLabel: 'ロッドホルダーだけ' }
];

const BAG_ITEMS = [
  '竿',
  'リール',
  '仕掛け',
  'クーラーボックス',
  '氷',
  '飲み物',
  '酔い止め',
  'タオル',
  'レインウェア',
  '現金'
];

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const hasSupabaseConfig = Boolean(supabaseUrl && supabaseAnonKey);
const supabase = hasSupabaseConfig ? createClient(supabaseUrl, supabaseAnonKey) : null;

function makeCellKey(memberKey, itemKey) {
  return `${memberKey}:${itemKey}`;
}

function App() {
  const [activePage, setActivePage] = useState('rental');

  return (
    <main className="appShell">
      <header className="appHeader">
        <div>
          <p className="eyebrow">釣行準備</p>
          <h1>釣り持ち物チェックリスト</h1>
        </div>
      </header>

      <nav className="tabs" aria-label="ページ切り替え">
        <button
          className={activePage === 'bag' ? 'tab active' : 'tab'}
          onClick={() => setActivePage('bag')}
          type="button"
        >
          持ち物
        </button>
        <button
          className={activePage === 'rental' ? 'tab active' : 'tab'}
          onClick={() => setActivePage('rental')}
          type="button"
        >
          レンタル確認
        </button>
      </nav>

      {activePage === 'bag' ? <BagChecklist /> : <RentalChecklist />}
    </main>
  );
}

function BagChecklist() {
  const [checkedItems, setCheckedItems] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('bagChecklist') || '{}');
    } catch {
      return {};
    }
  });

  useEffect(() => {
    localStorage.setItem('bagChecklist', JSON.stringify(checkedItems));
  }, [checkedItems]);

  return (
    <section className="panel" aria-labelledby="bag-title">
      <div className="sectionTitle">
        <h2 id="bag-title">持ち物</h2>
        <span>{Object.values(checkedItems).filter(Boolean).length} / {BAG_ITEMS.length}</span>
      </div>

      <div className="bagList">
        {BAG_ITEMS.map((item) => (
          <label className="bagItem" key={item}>
            <input
              checked={Boolean(checkedItems[item])}
              onChange={() =>
                setCheckedItems((current) => ({ ...current, [item]: !current[item] }))
              }
              type="checkbox"
            />
            <span>{item}</span>
          </label>
        ))}
      </div>
    </section>
  );
}

function RentalChecklist() {
  const [checks, setChecks] = useState({});
  const [loading, setLoading] = useState(hasSupabaseConfig);
  const [savingKey, setSavingKey] = useState('');
  const [error, setError] = useState('');

  const totals = useMemo(() => {
    return RENTAL_ITEMS.reduce((result, item) => {
      result[item.key] = MEMBERS.filter((member) => checks[makeCellKey(member.key, item.key)]).length;
      return result;
    }, {});
  }, [checks]);

  useEffect(() => {
    if (!supabase) return;

    let isMounted = true;

    async function loadChecks() {
      setLoading(true);
      setError('');

      const { data, error: loadError } = await supabase
        .from('rental_checks')
        .select('member_key,item_key,checked');

      if (!isMounted) return;

      if (loadError) {
        setError('レンタル確認を読み込めませんでした。Supabase設定とテーブルを確認してください。');
      } else {
        const nextChecks = {};
        data.forEach((row) => {
          nextChecks[makeCellKey(row.member_key, row.item_key)] = row.checked;
        });
        setChecks(nextChecks);
      }

      setLoading(false);
    }

    loadChecks();

    const channel = supabase
      .channel('rental-checks-shared')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'rental_checks' },
        (payload) => {
          const row = payload.new;
          if (!row?.member_key || !row?.item_key) return;

          setChecks((current) => ({
            ...current,
            [makeCellKey(row.member_key, row.item_key)]: row.checked
          }));
        }
      )
      .subscribe();

    return () => {
      isMounted = false;
      supabase.removeChannel(channel);
    };
  }, []);

  async function toggleCheck(memberKey, itemKey) {
    const cellKey = makeCellKey(memberKey, itemKey);
    const nextValue = !checks[cellKey];

    setChecks((current) => ({ ...current, [cellKey]: nextValue }));

    if (!supabase) {
      setError('Supabaseの環境変数が未設定です。.envにURLとanon keyを設定してください。');
      return;
    }

    setSavingKey(cellKey);
    setError('');

    const { error: saveError } = await supabase.from('rental_checks').upsert({
      member_key: memberKey,
      item_key: itemKey,
      checked: nextValue,
      updated_at: new Date().toISOString()
    });

    if (saveError) {
      setChecks((current) => ({ ...current, [cellKey]: !nextValue }));
      setError('保存に失敗しました。少し待ってからもう一度試してください。');
    }

    setSavingKey('');
  }

  async function resetAll() {
    const previousChecks = checks;
    const resetRows = MEMBERS.flatMap((member) =>
      RENTAL_ITEMS.map((item) => ({
        member_key: member.key,
        item_key: item.key,
        checked: false,
        updated_at: new Date().toISOString()
      }))
    );

    setChecks({});

    if (!supabase) {
      setChecks(previousChecks);
      setError('Supabaseの環境変数が未設定です。.envにURLとanon keyを設定してください。');
      return;
    }

    setError('');
    const { error: resetError } = await supabase.from('rental_checks').upsert(resetRows);

    if (resetError) {
      setChecks(previousChecks);
      setError('全リセットに失敗しました。ページを再読み込みして状態を確認してください。');
    }
  }

  return (
    <section className="panel rentalPanel" aria-labelledby="rental-title">
      <div className="sectionTitle">
        <div>
          <h2 id="rental-title">レンタル確認</h2>
          <p>全員で同じURLを開くと、同じチェック状態を見られます。</p>
        </div>
        <button className="resetButton" onClick={resetAll} type="button">
          全リセット
        </button>
      </div>

      {!hasSupabaseConfig && (
        <div className="notice">
          Supabaseの環境変数が未設定です。Vercelに
          <code>VITE_SUPABASE_URL</code> と <code>VITE_SUPABASE_ANON_KEY</code> を設定してください。
        </div>
      )}

      {error && <div className="notice error">{error}</div>}
      {loading && <div className="notice">読み込み中...</div>}

      <div className="tableWrap" aria-label="レンタル確認表">
        <table className="rentalTable">
          <thead>
            <tr>
              <th className="nameColumn">名前</th>
              {RENTAL_ITEMS.map((item) => (
                <th key={item.key}>{item.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MEMBERS.map((member) => (
              <tr key={member.key}>
                <th className="nameColumn" scope="row">{member.name}</th>
                {RENTAL_ITEMS.map((item) => {
                  const cellKey = makeCellKey(member.key, item.key);
                  const checked = Boolean(checks[cellKey]);

                  return (
                    <td key={item.key}>
                      <button
                        aria-label={`${member.name} ${item.fullLabel}`}
                        aria-pressed={checked}
                        className={checked ? 'checkCell checked' : 'checkCell'}
                        disabled={savingKey === cellKey}
                        onClick={() => toggleCheck(member.key, item.key)}
                        type="button"
                      >
                        {checked ? '✓' : ''}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="totals" aria-label="合計">
        {RENTAL_ITEMS.map((item) => (
          <div className="totalItem" key={item.key}>
            <span>{item.label}</span>
            <strong>{totals[item.key] ?? 0}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

createRoot(document.getElementById('root')).render(<App />);
