import { FC } from "react";

interface ConfirmDialogProps {
    isOpen: boolean;
    onCancel: () => void;
    onConfirm: () => void;
    text?: string;
}

const ConfirmDialog: FC<ConfirmDialogProps> = ({
                                                   isOpen,
                                                   onCancel,
                                                   onConfirm,
                                                   text = "Are you sure you want to delete the document?",
                                               }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-lg shadow-lg w-80 p-6">
                <p className="text-gray-800 text-center mb-6">{text}</p>
                <div className="flex justify-center space-x-4">
                    <button
                        onClick={onCancel}
                        className="px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-700"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white"
                    >
                        Yes
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ConfirmDialog;
