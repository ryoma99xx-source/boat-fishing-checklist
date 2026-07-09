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

const DEFAULT_LIST = {
  id: 'main',
  name: 'レンタル確認',
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

function normalizeList(list) {
  const members = Array.isArray(list?.members) ? list.members : DEFAULT_MEMBERS;
  const items = Array.isArray(list?.items) ? list.items : DEFAULT_RENTAL_ITEMS;

  return {
    id: list?.id || createKey('list'),
    name: String(list?.name || '新しいリスト').trim() || '新しいリスト',
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
  const [lists, setLists] = useState([DEFAULT_LIST]);
  const [selectedListId, setSelectedListId] = useState(() => {
    return localStorage.getItem('selectedRentalListId') || DEFAULT_LIST.id;
  });
  const [listsLoading, setListsLoading] = useState(hasSupabaseConfig);
  const [listsError, setListsError] = useState('');

  const selectedList = useMemo(() => {
    return lists.find((list) => list.id === selectedListId) || lists[0] || DEFAULT_LIST;
  }, [lists, selectedListId]);

  useEffect(() => {
    localStorage.setItem('selectedRentalListId', selectedList.id);
  }, [selectedList.id]);

  useEffect(() => {
    if (!supabase) return;

    let isMounted = true;

    async function loadLists() {
      setListsLoading(true);
      setListsError('');

      const { data, error } = await supabase
        .from('rental_config')
        .select('id,name,members,items')
        .order('updated_at', { ascending: true });

      if (!isMounted) return;

      if (error) {
        setListsError('リストを読み込めませんでした。SupabaseのSQLを更新してください。');
      } else if (data?.length) {
        const nextLists = data.map(normalizeList);
        setLists(nextLists);
        if (!nextLists.some((list) => list.id === selectedListId)) {
          setSelectedListId(nextLists[0].id);
        }
      } else {
        await saveList(DEFAULT_LIST);
      }

      setListsLoading(false);
    }

    loadLists();

    const channel = supabase
      .channel('rental-lists-shared')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'rental_config' },
        (payload) => {
          if (payload.eventType === 'DELETE') {
            const deletedId = payload.old?.id;
            setLists((current) => {
              const nextLists = current.filter((list) => list.id !== deletedId);
              if (deletedId === selectedListId && nextLists[0]) {
                setSelectedListId(nextLists[0].id);
              }
              return nextLists.length ? nextLists : [DEFAULT_LIST];
            });
            return;
          }

          if (payload.new) {
            const nextList = normalizeList(payload.new);
            setLists((current) => {
              const exists = current.some((list) => list.id === nextList.id);
              if (exists) {
                return current.map((list) => (list.id === nextList.id ? nextList : list));
              }
              return [...current, nextList];
            });
          }
        }
      )
      .subscribe();

    return () => {
      isMounted = false;
      supabase.removeChannel(channel);
    };
  }, [selectedListId]);

  async function saveList(nextList) {
    const cleanList = normalizeList(nextList);
    setLists((current) => {
      const exists = current.some((list) => list.id === cleanList.id);
      if (exists) {
        return current.map((list) => (list.id === cleanList.id ? cleanList : list));
      }
      return [...current, cleanList];
    });

    if (!supabase) {
      setListsError('Supabaseの環境変数が未設定です。Vercelの環境変数を確認してください。');
      return false;
    }

    const { error } = await supabase.from('rental_config').upsert({
      id: cleanList.id,
      name: cleanList.name,
      members: cleanList.members,
      items: cleanList.items,
      updated_at: new Date().toISOString()
    });

    if (error) {
      setListsError('リストの保存に失敗しました。SupabaseのSQLを更新してください。');
      return false;
    }

    setListsError('');
    return true;
  }

  async function createList(name) {
    const newList = {
      ...DEFAULT_LIST,
      id: createKey('list'),
      name: name.trim() || '新しいリスト',
      members: DEFAULT_MEMBERS,
      items: DEFAULT_RENTAL_ITEMS
    };
    const ok = await saveList(newList);
    if (ok) {
      setSelectedListId(newList.id);
      setActivePage('edit');
    }
    return ok;
  }

  async function deleteList(listId) {
    if (lists.length <= 1) {
      setListsError('リストは最低1つ必要です。');
      return false;
    }

    const nextSelectedId = lists.find((list) => list.id !== listId)?.id || DEFAULT_LIST.id;
    setLists((current) => current.filter((list) => list.id !== listId));
    setSelectedListId(nextSelectedId);

    if (!supabase) {
      setListsError('Supabaseの環境変数が未設定です。Vercelの環境変数を確認してください。');
      return false;
    }

    const { error: checksError } = await supabase
      .from('rental_checks')
      .delete()
      .eq('list_id', listId);
    const { error: listError } = await supabase
      .from('rental_config')
      .delete()
      .eq('id', listId);

    if (checksError || listError) {
      setListsError('リストの削除に失敗しました。ページを再読み込みして確認してください。');
      return false;
    }

    setListsError('');
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

      {activePage !== 'bag' && (
        <ListBar
          lists={lists}
          onCreateList={createList}
          onSelectList={setSelectedListId}
          selectedListId={selectedList.id}
        />
      )}

      {listsError && <div className="notice error">{listsError}</div>}
      {listsLoading && <div className="notice">リストを読み込み中...</div>}

      {activePage === 'bag' && <BagChecklist />}
      {activePage === 'rental' && <RentalChecklist list={selectedList} />}
      {activePage === 'edit' && (
        <ListEditor
          list={selectedList}
          listCount={lists.length}
          onDelete={deleteList}
          onSave={saveList}
        />
      )}
    </main>
  );
}

function ListBar({ lists, onCreateList, onSelectList, selectedListId }) {
  const [newListName, setNewListName] = useState('');
  const [creating, setCreating] = useState(false);

  async function handleCreate() {
    setCreating(true);
    const ok = await onCreateList(newListName);
    if (ok) {
      setNewListName('');
    }
    setCreating(false);
  }

  return (
    <section className="listBar" aria-label="リスト選択">
      <label className="listSelectLabel">
        <span>表示するリスト</span>
        <select value={selectedListId} onChange={(event) => onSelectList(event.target.value)}>
          {lists.map((list) => (
            <option key={list.id} value={list.id}>
              {list.name}
            </option>
          ))}
        </select>
      </label>
      <div className="newListBox">
        <input
          aria-label="新しいリスト名"
          onChange={(event) => setNewListName(event.target.value)}
          placeholder="新しいリスト名"
          type="text"
          value={newListName}
        />
        <button className="addButton" disabled={creating} onClick={handleCreate} type="button">
          {creating ? '作成中...' : '新規作成'}
        </button>
      </div>
    </section>
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

function RentalChecklist({ list }) {
  const { members, items } = list;
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
        .select('member_key,item_key,checked')
        .eq('list_id', list.id);

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
      .channel(`rental-checks-${list.id}`)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'rental_checks', filter: `list_id=eq.${list.id}` },
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
  }, [list.id]);

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
      list_id: list.id,
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
        list_id: list.id,
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
          <h2 id="rental-title">{list.name}</h2>
          <p>選択中のリストだけのチェック状態を共有します。</p>
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

function ListEditor({ list, listCount, onDelete, onSave }) {
  const [draft, setDraft] = useState(list);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    setDraft(list);
    setMessage('');
  }, [list]);

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
    const cleanName = draft.name.trim();
    const cleanMembers = draft.members
      .map((member) => ({ ...member, name: member.name.trim() }))
      .filter((member) => member.name);
    const cleanItems = draft.items
      .map((item) => ({ ...item, label: item.label.trim() }))
      .filter((item) => item.label);

    if (!cleanName) {
      setMessage('リスト名を入力してください。');
      return;
    }

    if (cleanMembers.length === 0 || cleanItems.length === 0) {
      setMessage('名前と項目はそれぞれ1つ以上必要です。');
      return;
    }

    setSaving(true);
    setMessage('');
    const ok = await onSave({
      id: draft.id,
      name: cleanName,
      members: cleanMembers,
      items: cleanItems
    });
    setSaving(false);
    setMessage(ok ? '保存しました。レンタル確認にも反映されます。' : '保存できませんでした。');
  }

  async function handleDelete() {
    if (listCount <= 1) {
      setMessage('リストは最低1つ必要です。');
      return;
    }

    const confirmed = window.confirm(`「${list.name}」を削除しますか？チェック状態も消えます。`);
    if (!confirmed) return;

    setDeleting(true);
    setMessage('');
    const ok = await onDelete(list.id);
    setDeleting(false);
    if (!ok) {
      setMessage('削除できませんでした。');
    }
  }

  return (
    <section className="panel" aria-labelledby="edit-title">
      <div className="sectionTitle">
        <div>
          <h2 id="edit-title">リスト編集</h2>
          <p>リスト名、縦軸の名前、横軸のチェック項目を編集できます。</p>
        </div>
        <button className="saveButton" disabled={saving} onClick={handleSave} type="button">
          {saving ? '保存中...' : '保存'}
        </button>
      </div>

      {message && <div className="notice">{message}</div>}

      <label className="nameField">
        <span>リスト名</span>
        <input
          onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
          placeholder="例：7月20日 午前船"
          type="text"
          value={draft.name}
        />
      </label>

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

      <div className="dangerArea">
        <button
          className="deleteListButton"
          disabled={deleting || listCount <= 1}
          onClick={handleDelete}
          type="button"
        >
          {deleting ? '削除中...' : 'このリストを削除'}
        </button>
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
