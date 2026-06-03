    count = raw_inputs.get("cluster_count", 0)
        if shap_val > 0:
            return f"compounding hazard density ({count} instances elevating risk)"
        else:
            return f"low damage density ({count} instance(s), reducing urgency)"