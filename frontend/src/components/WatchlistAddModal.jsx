import React, { useState } from 'react';
import { X, BarChart2, Calendar, Type, Plus, AlertTriangle } from 'lucide-react';

/**
 * Modal for adding new watchlist items
 */
export default function WatchlistAddModal({ isOpen, onClose, onSubmit }) {
  const [formData, setFormData] = useState({
    name: '',
    watch_type: 'indicator',
    condition: '',
    target_value: '',
    target_date: '',
    keywords: '',
    related_indicators: [],
    expected_impact: '',
    notes: '',
  });

  const [errors, setErrors] = useState({});

  if (!isOpen) return null;

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (formData.watch_type === 'indicator' && !formData.condition.trim()) {
      newErrors.condition = 'Condition is required for indicator watch';
    }
    if (formData.watch_type === 'date' && !formData.target_date) {
      newErrors.target_date = 'Target date is required';
    }
    if (formData.watch_type === 'keyword' && !formData.keywords.trim()) {
      newErrors.keywords = 'Keywords are required for keyword watch';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      onSubmit?.(formData);
      handleClose();
    }
  };

  const handleClose = () => {
    setFormData({
      name: '',
      watch_type: 'indicator',
      condition: '',
      target_value: '',
      target_date: '',
      keywords: '',
      related_indicators: [],
      expected_impact: '',
      notes: '',
    });
    setErrors({});
    onClose?.();
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'indicator': return <BarChart2 className="w-5 h-5" />;
      case 'date': return <Calendar className="w-5 h-5" />;
      case 'keyword': return <Type className="w-5 h-5" />;
      default: return <AlertTriangle className="w-5 h-5" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />
      
      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-xl">
          <div className="flex items-center gap-3">
            <Plus className="w-6 h-6 text-primary-600" />
            <h2 className="text-xl font-semibold text-gray-900">Add New Watch</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Watch Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Watch Type</label>
            <div className="grid grid-cols-3 gap-3">
              {['indicator', 'date', 'keyword'].map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleChange('watch_type', type)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all ${
                    formData.watch_type === type
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-gray-200 hover:border-gray-300 text-gray-600'
                  }`}
                >
                  {getTypeIcon(type)}
                  <span className="text-sm font-medium capitalize">{type}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="e.g., Interbank ON Rate > 9%"
              className={`w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                errors.name ? 'border-red-500' : 'border-gray-200'
              }`}
            />
            {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name}</p>}
          </div>

          {/* Indicator Watch Fields */}
          {formData.watch_type === 'indicator' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Condition *</label>
                <input
                  type="text"
                  value={formData.condition}
                  onChange={(e) => handleChange('condition', e.target.value)}
                  placeholder="e.g., interbank_on > 9.0"
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                    errors.condition ? 'border-red-500' : 'border-gray-200'
                  }`}
                />
                {errors.condition && <p className="text-red-500 text-xs mt-1">{errors.condition}</p>}
                <p className="text-xs text-gray-400 mt-1">Format: indicator_id {">"} or {"<"} value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Target Value</label>
                <input
                  type="number"
                  step="any"
                  value={formData.target_value}
                  onChange={(e) => handleChange('target_value', e.target.value)}
                  placeholder="e.g., 9.0"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </>
          )}

          {/* Date Watch Fields */}
          {formData.watch_type === 'date' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Date *</label>
              <input
                type="date"
                value={formData.target_date}
                onChange={(e) => handleChange('target_date', e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                  errors.target_date ? 'border-red-500' : 'border-gray-200'
                }`}
              />
              {errors.target_date && <p className="text-red-500 text-xs mt-1">{errors.target_date}</p>}
            </div>
          )}

          {/* Keyword Watch Fields */}
          {formData.watch_type === 'keyword' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Keywords *</label>
              <textarea
                value={formData.keywords}
                onChange={(e) => handleChange('keywords', e.target.value)}
                placeholder="Enter keywords separated by commas, e.g., Fed hawkish, rate hike, FOMC"
                rows={3}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                  errors.keywords ? 'border-red-500' : 'border-gray-200'
                }`}
              />
              {errors.keywords && <p className="text-red-500 text-xs mt-1">{errors.keywords}</p>}
            </div>
          )}

          {/* Expected Impact */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Expected Impact (optional)</label>
            <textarea
              value={formData.expected_impact}
              onChange={(e) => handleChange('expected_impact', e.target.value)}
              placeholder="What might happen when this triggers? (each line is one impact)"
              rows={3}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              placeholder="Any additional context or notes..."
              rows={2}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Watch
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
