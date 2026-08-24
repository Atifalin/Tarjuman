import React, { useState, useEffect } from 'react';
import {
  Database,
  Plus,
  Trash2,
  Download,
  Upload,
  Search,
  BookOpen,
  CheckCircle2,
  FileSpreadsheet
} from 'lucide-react';
import { GlossaryItem } from '../../types';
import { api } from '../../services/api';

export const GlossaryManager: React.FC = () => {
  const [terms, setTerms] = useState<GlossaryItem[]>([]);
  const [tmList, setTmList] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'glossary' | 'tm'>('glossary');

  // New Term Form
  const [showAddForm, setShowAddForm] = useState(false);
  const [newArabic, setNewArabic] = useState('');
  const [newUrdu, setNewUrdu] = useState('');
  const [newCategory, setNewCategory] = useState('General');
  const [newNotes, setNewNotes] = useState('');

  const loadData = async () => {
    try {
      const g = await api.getGlossaryTerms();
      setTerms(g);
      const tm = await api.getTranslationMemory();
      setTmList(tm);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddTerm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newArabic.trim() || !newUrdu.trim()) return;

    try {
      await api.addGlossaryTerm({
        source_arabic: newArabic.trim(),
        target_urdu: newUrdu.trim(),
        category: newCategory.trim(),
        notes: newNotes.trim(),
      });
      setNewArabic('');
      setNewUrdu('');
      setNewNotes('');
      setShowAddForm(false);
      loadData();
    } catch (e: any) {
      alert(`Failed to add term: ${e.message}`);
    }
  };

  const handleDeleteTerm = async (id: string) => {
    if (!confirm('Are you sure you want to delete this glossary term?')) return;
    try {
      await api.deleteGlossaryTerm(id);
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const filteredTerms = terms.filter(
    (t) =>
      t.source_arabic.includes(search) ||
      t.target_urdu.includes(search) ||
      t.category?.toLowerCase().includes(search.toLowerCase())
  );

  const filteredTm = tmList.filter(
    (m) =>
      m.source_arabic.includes(search) ||
      m.approved_urdu.includes(search)
  );

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-400" />
            Terminology & Translation Memory
          </h2>
          <p className="text-xs text-slate-400">
            Maintain custom theological, academic, and named terminology rules and recall approved sentences.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-xl transition-colors shadow-md"
          >
            <Plus className="w-4 h-4" />
            Add New Term
          </button>

          <a
            href="http://127.0.0.1:8000/api/glossary/export-csv"
            download
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs px-3.5 py-2 rounded-xl font-medium transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </a>
        </div>
      </div>

      {/* Tabs & Search */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('glossary')}
            className={`text-xs font-bold px-4 py-2 rounded-xl transition-colors ${
              activeTab === 'glossary'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Glossary Dictionary ({terms.length})
          </button>

          <button
            onClick={() => setActiveTab('tm')}
            className={`text-xs font-bold px-4 py-2 rounded-xl transition-colors ${
              activeTab === 'tm'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Translation Memory Cache ({tmList.length})
          </button>
        </div>

        <div className="flex items-center gap-2 bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800 w-72">
          <Search className="w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search terms or phrases..."
            className="bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none w-full"
          />
        </div>
      </div>

      {/* Add Term Form Modal */}
      {showAddForm && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleAddTerm}
            className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 space-y-4"
          >
            <h3 className="text-base font-bold text-white">Add Glossary Term</h3>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Arabic Source Term</label>
              <input
                type="text"
                required
                value={newArabic}
                onChange={(e) => setNewArabic(e.target.value)}
                placeholder="e.g. الصلاة"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs font-arabic text-lg text-slate-100"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Preferred Urdu Translation</label>
              <input
                type="text"
                required
                value={newUrdu}
                onChange={(e) => setNewUrdu(e.target.value)}
                placeholder="e.g. نماز"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs font-urdu text-xl text-slate-100"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Category</label>
                <input
                  type="text"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  placeholder="Fiqh / Hadith / Names"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Notes (Optional)</label>
                <input
                  type="text"
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="Context notes"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 bg-slate-800 text-slate-300 text-xs rounded-xl hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-md"
              >
                Save Term
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 1: GLOSSARY TABLE */}
      {activeTab === 'glossary' && (
        <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="p-4">Arabic Term</th>
                <th className="p-4">Preferred Urdu Translation</th>
                <th className="p-4">Category</th>
                <th className="p-4">Notes</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {filteredTerms.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500">
                    No glossary terms found matching your query.
                  </td>
                </tr>
              ) : (
                filteredTerms.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-950/40 transition-colors">
                    <td className="p-4 font-arabic text-lg text-slate-100">{t.source_arabic}</td>
                    <td className="p-4 font-urdu text-xl text-emerald-300">{t.target_urdu}</td>
                    <td className="p-4">
                      <span className="bg-slate-950 px-2 py-1 rounded text-[11px] border border-slate-800 text-slate-400">
                        {t.category || 'General'}
                      </span>
                    </td>
                    <td className="p-4 text-slate-400 text-xs">{t.notes || '—'}</td>
                    <td className="p-4 text-right">
                      {t.id && (
                        <button
                          onClick={() => handleDeleteTerm(t.id!)}
                          className="p-1.5 bg-slate-800 hover:bg-rose-900/40 hover:text-rose-400 text-slate-400 rounded-lg transition-colors"
                          title="Delete Term"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 2: TRANSLATION MEMORY */}
      {activeTab === 'tm' && (
        <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="p-4">Source Arabic Sentence</th>
                <th className="p-4">Approved Urdu Translation</th>
                <th className="p-4">Reuse Count</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {filteredTm.length === 0 ? (
                <tr>
                  <td colSpan={3} className="p-8 text-center text-slate-500">
                    No approved sentences in Translation Memory yet. As you approve chunks in Review Mode, they will be cached here automatically.
                  </td>
                </tr>
              ) : (
                filteredTm.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-950/40 transition-colors">
                    <td className="p-4 font-arabic text-base text-slate-200">{m.source_arabic}</td>
                    <td className="p-4 font-urdu text-xl text-emerald-300">{m.approved_urdu}</td>
                    <td className="p-4 font-mono font-bold text-indigo-400">{m.usage_count}x</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
};
