package com.example.warehouse.ui;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageButton;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.example.warehouse.R;
import com.example.warehouse.data.model.InventoryItem;

import java.util.ArrayList;
import java.util.List;

public class ItemAdapter extends RecyclerView.Adapter<ItemAdapter.VH> {

    public interface OnDeleteClick {
        void onDelete(InventoryItem item);
    }

    private final List<InventoryItem> data = new ArrayList<>();
    private final OnDeleteClick onDelete;

    public ItemAdapter(OnDeleteClick onDelete) {
        this.onDelete = onDelete;
    }

    public void setData(List<InventoryItem> newData) {
        data.clear();
        if (newData != null) data.addAll(newData);
        notifyDataSetChanged();
    }

    public void removeItem(InventoryItem item) {
        int index = data.indexOf(item);
        if (index >= 0) {
            data.remove(index);
            notifyItemRemoved(index);
        }
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_product, parent, false);
        return new VH(v);
    }

    @Override
    public void onBindViewHolder(@NonNull VH holder, int position) {
        InventoryItem item = data.get(position);
        holder.tvName.setText(item.productName != null ? item.productName : "Товар #" + item.productId);
        holder.tvSku.setText("SKU: " + (item.sku != null ? item.sku : "—"));
        holder.tvWeight.setText(String.format("Нетто: %.2f кг", item.netWeight));
        holder.btnDelete.setOnClickListener(v -> onDelete.onDelete(item));
    }

    @Override
    public int getItemCount() {
        return data.size();
    }

    static class VH extends RecyclerView.ViewHolder {
        final TextView tvName;
        final TextView tvSku;
        final TextView tvWeight;
        final ImageButton btnDelete;

        VH(@NonNull View itemView) {
            super(itemView);
            tvName = itemView.findViewById(R.id.tvName);
            tvSku = itemView.findViewById(R.id.tvSku);
            tvWeight = itemView.findViewById(R.id.tvWeight);
            btnDelete = itemView.findViewById(R.id.btnDelete);
        }
    }
}