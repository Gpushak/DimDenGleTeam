package com.example.warehouse.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.core.content.ContextCompat;

import com.example.warehouse.R;
import com.example.warehouse.data.model.BoxContents;
import com.example.warehouse.data.model.BoxNode;
import com.example.warehouse.ui.Weights;

import java.util.ArrayList;
import java.util.List;

/**
 * Ададер списка: вложенные ячейки (коробки) + товары текущей ячейки.
 */
public class WarehouseAdapter extends BaseAdapter {

    public static class Row {
        public final boolean isBox;
        public BoxNode box;
        public BoxContents.ItemRow item;

        private Row(boolean isBox, BoxNode box, BoxContents.ItemRow item) {
            this.isBox = isBox;
            this.box = box;
            this.item = item;
        }

        public static Row ofBox(BoxNode box) {
            return new Row(true, box, null);
        }

        public static Row ofItem(BoxContents.ItemRow item) {
            return new Row(false, null, item);
        }
    }

    private final Context context;
    private final List<Row> rows = new ArrayList<>();

    public WarehouseAdapter(Context context) {
        this.context = context;
    }

    public void setRows(List<Row> newRows) {
        rows.clear();
        if (newRows != null) {
            rows.addAll(newRows);
        }
        notifyDataSetChanged();
    }

    @Override
    public int getCount() {
        return rows.size();
    }

    @Override
    public Row getItem(int position) {
        return rows.get(position);
    }

    @Override
    public long getItemId(int position) {
        return position;
    }

    @Override
    public View getView(int position, View convertView, ViewGroup parent) {
        if (convertView == null) {
            convertView = LayoutInflater.from(context)
                    .inflate(R.layout.item_row, parent, false);
        }

        Row row = getItem(position);
        ImageView icon = convertView.findViewById(R.id.icon);
        TextView title = convertView.findViewById(R.id.title);
        TextView subtitle = convertView.findViewById(R.id.subtitle);
        TextView chevron = convertView.findViewById(R.id.chevron);

        if (row.isBox) {
            title.setText(row.box.name);
            String type = row.box.box_type_name != null
                    ? row.box.box_type_name
                    : context.getString(R.string.cell_fallback);
            subtitle.setText(context.getString(
                    R.string.box_subtitle, type, row.box.childrenCount()));
            icon.setImageDrawable(
                    ContextCompat.getDrawable(context, R.drawable.ic_box));
            chevron.setVisibility(View.VISIBLE);
        } else {
            title.setText(row.item.item_type_name);
            StringBuilder sb = new StringBuilder();
            if (row.item.box_name != null) {
                sb.append(row.item.box_name).append(" · ");
            }
            sb.append(context.getString(R.string.item_qty, row.item.quantity));
            if (row.item.total_weight_g != null) {
                sb.append(" · ").append(Weights.format(context, row.item.total_weight_g));
            }
            sb.append(" · ").append(context.getString(R.string.item_actions_hint));
            subtitle.setText(sb);
            icon.setImageDrawable(
                    ContextCompat.getDrawable(context, R.drawable.ic_item));
            chevron.setVisibility(View.GONE);
        }

        return convertView;
    }
}
