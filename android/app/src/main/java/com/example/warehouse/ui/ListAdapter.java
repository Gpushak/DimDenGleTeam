package com.example.warehouse.ui;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.example.warehouse.R;
import com.example.warehouse.data.model.InventoryList;

import java.util.ArrayList;
import java.util.List;

public class ListAdapter extends RecyclerView.Adapter<ListAdapter.VH> {

    public interface OnItemClick {
        void onClick(InventoryList list);
    }

    private final List<InventoryList> data = new ArrayList<>();
    private final OnItemClick onClick;

    public ListAdapter(OnItemClick onClick) {
        this.onClick = onClick;
    }

    public void setData(List<InventoryList> newData) {
        data.clear();
        if (newData != null) data.addAll(newData);
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_list, parent, false);
        return new VH(v);
    }

    @Override
    public void onBindViewHolder(@NonNull VH holder, int position) {
        InventoryList item = data.get(position);
        holder.tvName.setText(item.name);
        holder.tvStatus.setText("Статус: " + item.status);
        holder.tvCount.setText("Позиций: " + item.itemsCount);
        holder.itemView.setOnClickListener(v -> onClick.onClick(item));
    }

    @Override
    public int getItemCount() {
        return data.size();
    }

    static class VH extends RecyclerView.ViewHolder {
        final TextView tvName;
        final TextView tvStatus;
        final TextView tvCount;

        VH(@NonNull View itemView) {
            super(itemView);
            tvName = itemView.findViewById(R.id.tvName);
            tvStatus = itemView.findViewById(R.id.tvStatus);
            tvCount = itemView.findViewById(R.id.tvCount);
        }
    }
}