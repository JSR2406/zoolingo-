import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react';

// Toast Context
export const ToastContext = React.createContext(null);

// Toast types
const TOAST_TYPES = {
    success: {
        icon: CheckCircle,
        bgColor: 'bg-emerald-500/20',
        borderColor: 'border-emerald-500/50',
        textColor: 'text-emerald-400',
        iconColor: 'text-emerald-400'
    },
    error: {
        icon: XCircle,
        bgColor: 'bg-red-500/20',
        borderColor: 'border-red-500/50',
        textColor: 'text-red-400',
        iconColor: 'text-red-400'
    },
    warning: {
        icon: AlertCircle,
        bgColor: 'bg-amber-500/20',
        borderColor: 'border-amber-500/50',
        textColor: 'text-amber-400',
        iconColor: 'text-amber-400'
    },
    info: {
        icon: AlertCircle,
        bgColor: 'bg-blue-500/20',
        borderColor: 'border-blue-500/50',
        textColor: 'text-blue-400',
        iconColor: 'text-blue-400'
    }
};

const Toast = ({ id, type, title, message, onDismiss }) => {
    const config = TOAST_TYPES[type] || TOAST_TYPES.info;
    const Icon = config.icon;

    useEffect(() => {
        const timer = setTimeout(() => {
            onDismiss(id);
        }, 5000);
        return () => clearTimeout(timer);
    }, [id, onDismiss]);

    return (
        <motion.div
            initial={{ opacity: 0, x: 100, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.9 }}
            className={`
                flex items-start gap-3 p-4 rounded-xl border backdrop-blur-lg
                ${config.bgColor} ${config.borderColor}
                shadow-xl max-w-sm
            `}
        >
            <Icon className={`w-5 h-5 mt-0.5 ${config.iconColor} flex-shrink-0`} />
            <div className="flex-1 min-w-0">
                {title && (
                    <p className={`font-semibold ${config.textColor}`}>{title}</p>
                )}
                {message && (
                    <p className="text-text-secondary text-sm mt-0.5">{message}</p>
                )}
            </div>
            <button
                onClick={() => onDismiss(id)}
                className="text-text-muted hover:text-text-secondary transition-colors"
            >
                <X className="w-4 h-4" />
            </button>
        </motion.div>
    );
};

export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = (type, title, message) => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, type, title, message }]);
        return id;
    };

    const dismissToast = (id) => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
    };

    const toast = {
        success: (title, message) => addToast('success', title, message),
        error: (title, message) => addToast('error', title, message),
        warning: (title, message) => addToast('warning', title, message),
        info: (title, message) => addToast('info', title, message),
    };

    return (
        <ToastContext.Provider value={toast}>
            {children}
            <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
                <AnimatePresence>
                    {toasts.map(t => (
                        <Toast
                            key={t.id}
                            id={t.id}
                            type={t.type}
                            title={t.title}
                            message={t.message}
                            onDismiss={dismissToast}
                        />
                    ))}
                </AnimatePresence>
            </div>
        </ToastContext.Provider>
    );
};

export const useToast = () => {
    const context = React.useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};
