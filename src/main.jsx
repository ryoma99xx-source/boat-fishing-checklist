import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createClient } from '@supabase/supabase-js';
import './styles.css';

const DEFAULT_MEMBERS = [
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

const DEFAULT_RENTAL_ITEMS = [
  { key: 'full_set', label: 'フルセット' },
  { key: 'bishi', label: 'ビシのみ' },
  { key: 'iwashi', label: 'イワシ' },
  { key: 'rod_holder', label: 'ロッドホルダーだけ' }
];

const DEFAULT_CONFIG = {
  members: DEFAULT_MEMBERS,
  items: DEFAULT_RENTAL_ITEMS
};

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

function createKey(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeConfig(config) {
  const members = Array.isArray(config?.members) ? config.members : DEFAULT_MEMBERS;
  const items = Array.isArray(config?.items) ? config.items : DEFAULT_RENTAL_ITEMS;

  return {
    members: members
      .filter((member) => member?.key && member?.name)
      .map((member) => ({ key: member.key, name: member.name })),
    items: items
      .filter((item) => item?.key && item?.label)
      .map((item) => ({ key: item.key, label: item.label }))
  };
}

function App() {
  const [activePage, setActivePage] = useState('rental');
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [configLoading, setConfigLoading] = useState(hasSupabaseConfig);
  const [configError, setConfigError] = useState('');

  useEffect(() => {
    if (!supabase) return;

    let isMounted = true;

    async function loadConfig() {
      setConfigLoading(true);
      setConfigError('');

      const { data, error } = await supabase
        .from('rental_config')
        .select('members,items')
        .eq('id', 'main')
        .maybeSingle();

      if (!isMounted) return;

      if (error) {
        setConfigError('リスト設定を読み込めませんでした。SupabaseのSQLを更新してください。');
      } else if (data) {
        setConfig(normalizeConfig(data));
      } else {
        await saveConfig(DEFAULT_CONFIG);
      }

      setConfigLoading(false);
    }

    loadConfig();

    const channel = supabase
      .channel('rental-config-shared')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'rental_config', filter: 'id=eq.main' },
        (payload) => {
          if (payload.new) {
            setConfig(normalizeConfig(payload.new));
          }
        }
      )
      .subscribe();

    return () => {
      isMounted = false;
      supabase.removeChannel(channel);
    };
  }, []);

  async function saveConfig(nextConfig) {
    const cleanConfig = normalizeConfig(nextConfig);
    setConfig(cleanConfig);

    if (!supabase) {
      setConfigError('Supabaseの環境変数が未設定です。Vercelの環境変数を確認してください。');
      return false;
    }

    const { error } = await supabase.from('rental_config').upsert({
      id: 'main',
      members: cleanConfig.members,
      items: cleanConfig.items,
      updated_at: new Date().toISOString()
    });

    if (error) {
      setConfigError('リスト設定の保存に失敗しました。SupabaseのSQLを更新してください。');
      return false;
    }

    setConfigError('');
    return true;
  }

  return (
    <main className="appShell">
      <header className="appHeader">
        <div>
          <p className="eyebrow">釣行準備</p>
          <h1>釣り持ち物チェックリスト</h1>
        </div>
      </header>

      <nav className="tabs threeTabs" aria-label="ページ切り替え">
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
        <button
          className={activePage === 'edit' ? 'tab active' : 'tab'}
          onClick={() => setActivePage('edit')}
          type="button"
        >
          リスト編集
        </button>
      </nav>

      {configError && <div className="notice error">{configError}</div>}
      {configLoading && <div className="notice">リスト設定を読み込み中...</div>}

      {activePage === 'bag' && <BagChecklist />}
      {activePage === 'rental' && <RentalChecklist config={config} />}
      {activePage === 'edit' && <ListEditor config={config} onSave={saveConfig} />}
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

function RentalChecklist({ config }) {
  const { members, items } = config;
  const [checks, setChecks] = useState({});
  const [loading, setLoading] = useState(hasSupabaseConfig);
  const [savingKey, setSavingKey] = useState('');
  const [error, setError] = useState('');

  const totals = useMemo(() => {
    return items.reduce((result, item) => {
      result[item.key] = members.filter((member) => checks[makeCellKey(member.key, item.key)]).length;
      return result;
    }, {});
  }, [checks, items, members]);

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
    const resetRows = members.flatMap((member) =>
      items.map((item) => ({
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
              {items.map((item) => (
                <th key={item.key}>{item.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.key}>
                <th className="nameColumn" scope="row">{member.name}</th>
                {items.map((item) => {
                  const cellKey = makeCellKey(member.key, item.key);
                  const checked = Boolean(checks[cellKey]);

                  return (
                    <td key={item.key}>
                      <button
                        aria-label={`${member.name} ${item.label}`}
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
        {items.map((item) => (
          <div className="totalItem" key={item.key}>
            <span>{item.label}</span>
            <strong>{totals[item.key] ?? 0}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function ListEditor({ config, onSave }) {
  const [draft, setDraft] = useState(config);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    setDraft(config);
  }, [config]);

  function updateMember(key, name) {
    setDraft((current) => ({
      ...current,
      members: current.members.map((member) =>
        member.key === key ? { ...member, name } : member
      )
    }));
  }

  function updateItem(key, label) {
    setDraft((current) => ({
      ...current,
      items: current.items.map((item) =>
        item.key === key ? { ...item, label } : item
      )
    }));
  }

  function addMember() {
    setDraft((current) => ({
      ...current,
      members: [...current.members, { key: createKey('member'), name: '' }]
    }));
  }

  function addItem() {
    setDraft((current) => ({
      ...current,
      items: [...current.items, { key: createKey('item'), label: '' }]
    }));
  }

  function removeMember(key) {
    setDraft((current) => ({
      ...current,
      members: current.members.filter((member) => member.key !== key)
    }));
  }

  function removeItem(key) {
    setDraft((current) => ({
      ...current,
      items: current.items.filter((item) => item.key !== key)
    }));
  }

  async function handleSave() {
    const cleanMembers = draft.members
      .map((member) => ({ ...member, name: member.name.trim() }))
      .filter((member) => member.name);
    const cleanItems = draft.items
      .map((item) => ({ ...item, label: item.label.trim() }))
      .filter((item) => item.label);

    if (cleanMembers.length === 0 || cleanItems.length === 0) {
      setMessage('名前と項目はそれぞれ1つ以上必要です。');
      return;
    }

    setSaving(true);
    setMessage('');
    const ok = await onSave({ members: cleanMembers, items: cleanItems });
    setSaving(false);
    setMessage(ok ? '保存しました。レンタル確認にも反映されます。' : '保存できませんでした。');
  }

  return (
    <section className="panel" aria-labelledby="edit-title">
      <div className="sectionTitle">
        <div>
          <h2 id="edit-title">リスト編集</h2>
          <p>縦軸の名前と、横軸のチェック項目を編集できます。</p>
        </div>
        <button className="saveButton" disabled={saving} onClick={handleSave} type="button">
          {saving ? '保存中...' : '保存'}
        </button>
      </div>

      {message && <div className="notice">{message}</div>}

      <div className="editorGrid">
        <EditorSection
          addLabel="名前を追加"
          items={draft.members}
          label="縦軸（なまえ）"
          onAdd={addMember}
          onChange={updateMember}
          onRemove={removeMember}
          placeholder="名前"
          valueKey="name"
        />
        <EditorSection
          addLabel="項目を追加"
          items={draft.items}
          label="横軸（項目）"
          onAdd={addItem}
          onChange={updateItem}
          onRemove={removeItem}
          placeholder="項目名"
          valueKey="label"
        />
      </div>
    </section>
  );
}

function EditorSection({ addLabel, items, label, onAdd, onChange, onRemove, placeholder, valueKey }) {
  return (
    <div className="editorSection">
      <div className="editorHeading">
        <h3>{label}</h3>
        <button className="addButton" onClick={onAdd} type="button">
          ＋ {addLabel}
        </button>
      </div>

      <div className="editList">
        {items.map((item, index) => (
          <div className="editRow" key={item.key}>
            <span className="rowNumber">{index + 1}</span>
            <input
              aria-label={`${label} ${index + 1}`}
              onChange={(event) => onChange(item.key, event.target.value)}
              placeholder={placeholder}
              type="text"
              value={item[valueKey]}
            />
            <button
              aria-label={`${item[valueKey] || placeholder}を削除`}
              className="deleteButton"
              onClick={() => onRemove(item.key)}
              type="button"
            >
              削除
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
