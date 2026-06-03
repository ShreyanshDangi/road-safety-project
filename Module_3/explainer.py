"""
Module 3 — Smart Router
Step 3: SHAP Explainability → Human-Readable Reason String (Context-Enriched)
"""

def _describe_feature(feat_name, raw_inputs):
    """
    Convert a specific feature's name and the user's raw input value 
    into a readable phrase that explains the physical domain risk.
    """
    if feat_name.startswith("damage_class_"):
        val = feat_name.replace("damage_class_", "")
        if val == "Pothole":
            return f"acute blowout risk ({val})"
        elif val == "Alligator":
            return f"widespread structural subbase failure ({val} cracking)"
        else:
            return f"surface-level degradation ({val} crack)"
        
    elif feat_name.startswith("road_type_"):
        val = feat_name.replace("road_type_", "")
        if "highway" in val:
            return f"high-speed kinetic vulnerability ({val.replace('_', ' ').title()})"
        elif val == "city_road":
            return f"high traffic volume impact (City Road)"
        else:
            return f"localized traffic routing ({val.replace('_', ' ').title()})"
        
    elif feat_name == "relative_bbox_area":
        pct = raw_inputs.get("relative_bbox_area", 0) * 100
        if pct > 25:
            return f"massive physical footprint ({pct:.0f}% of frame)"
        else:
            return f"visible hazard area ({pct:.0f}% of frame)"
            
    elif feat_name == "cluster_count":
        count = raw_inputs.get("cluster_count", 0)
        if shap_val > 0:
            return f"compounding hazard density ({count} instances elevating risk)"
        else:
            return f"low damage density ({count} instance(s), reducing urgency)"
            
    return None


def generate_reason(raw_inputs, shap_impacts_dict, top_k=2):
    """
    Generates a context-aware reason string, ignoring features not present in the input.
    """
    importances = sorted(
        shap_impacts_dict.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )

    phrases = []
    
    for feat_name, shap_val in importances:
        # Filter out OHE features that are NOT in the raw input
        if feat_name.startswith("damage_class_"):
            if raw_inputs.get("damage_class") != feat_name.replace("damage_class_", ""):
                continue 
                
        elif feat_name.startswith("road_type_"):
            if raw_inputs.get("road_type") != feat_name.replace("road_type_", ""):
                continue 
        
        phrase = _describe_feature(feat_name, raw_inputs)
        
        if phrase and phrase not in phrases:
            phrases.append(phrase)
            
        if len(phrases) == top_k:
            break

    if not phrases:
        return "Priority determined from combined damage and location factors."

    # Join the phrases with a dynamic connector to make it read naturally
    if len(phrases) == 2:
        reason = "Prioritized due to " + phrases[0] + " compounding with " + phrases[1] + "."
    else:
        reason = "Prioritized due to " + phrases[0] + "."
        
    return reason