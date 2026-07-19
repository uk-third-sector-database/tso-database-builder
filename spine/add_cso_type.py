"""
Add cso_type and cso_subtype fields to the TSCS Spine dataset.

This is the final post-processing step of the spine build: it takes the
built spine CSV plus the SIC codes lookup and appends the two
classification columns documented in the Organisation Register guidance.
Classification logic was ported from dcms-report/dcms-report-v3.R (Step 2).
The July 2026 review found that the earlier vectorised implementation allowed
later rules to overwrite earlier rules even though the documented method is
first-match-wins. The corrected implementation below enforces that priority;
its one-off subtype delta is therefore a deliberate methodology correction,
not an attempt to reproduce the affected v1.0 subtype values.

Do not reorder the subtype rules: classification uses sequential masking
(first matching rule wins), so rule order is part of the method.

cso_type (4 categories):
  - Charity: orgs from CCEW, OSCR, or CCNI (and not CIC)
  - CIC: any org flagged is_cic == True
  - Co-operative / Mutual: orgs from Co-operatives or Mutuals Public Register
  - Other: everything else

cso_subtype (15 categories):
  - Charity, CIC, Co-operative / Mutual pass through unchanged.
  - "Other" is disaggregated using SIC codes + name patterns into:
    Housing Association, Dormant Company, Property Management Company,
    Education Institution, Sports Club, Religious Organisation,
    Arts Organisation, Health Organisation, Social Services Organisation,
    Professional / Trade Body, Membership Organisation,
    Other Company Limited By Guarantee (residual).
"""

import numpy as np
import pandas as pd


def add_cso_type(spine: pd.DataFrame) -> pd.DataFrame:
    """Add cso_type column using vectorized conditions."""
    is_cic = spine["is_cic"]
    src = spine["source_register"]

    charity_sources = {
        "Charity Commission for England and Wales",
        "Scottish Charity Register",
        "Charity Commission for Northern Ireland",
    }
    coop_sources = {"Co-operatives", "Mutuals Public Register"}

    conditions = [
        is_cic,
        src.isin(charity_sources),
        src.isin(coop_sources),
    ]
    choices = ["CIC", "Charity", "Co-operative / Mutual"]

    spine["cso_type"] = np.select(conditions, choices, default="Other")
    return spine


def add_cso_subtype(
    spine: pd.DataFrame, sic_primary: pd.DataFrame
) -> pd.DataFrame:
    """Add cso_subtype column using vectorized conditions.

    For Charity, CIC, Co-operative / Mutual: subtype == type.
    For Other: disaggregate using SIC + name patterns.
    """
    # Join SIC data
    spine = spine.merge(sic_primary[["uid", "primary_sic", "sic_div"]], on="uid", how="left")

    name_upper = spine["organisationname"].fillna("").str.upper()
    src = spine["source_register"]
    sic = spine["primary_sic"]
    div = spine["sic_div"]
    is_other = spine["cso_type"] == "Other"

    # Start with cso_type as default subtype
    subtype = spine["cso_type"].copy()

    # Apply classification rules with sequential masking: first match wins.
    # The "unclassified" mask narrows as each rule fires.
    unclassified = is_other.copy()

    rules: list[tuple[str, pd.Series]] = [
        # Housing Association
        (
            "Housing Association",
            unclassified
            & (
                src.isin({"Social Housing England", "Scottish Housing Regulator"})
                | name_upper.str.contains(
                    r"HOUSING ASSOCIATION|HOUSING SOCIETY|ALMSHOUSE",
                    na=False,
                    regex=True,
                )
            ),
        ),
        # Dormant Company
        ("Dormant Company", unclassified & (sic == 99999)),
        # Property Management Company
        (
            "Property Management Company",
            unclassified
            & (
                (div == 68)
                | name_upper.str.contains(
                    r"MANAGEMENT COMPANY|MANAGEMENT LIMITED|\bRTM\b|RIGHT TO MANAGE|FREEHOLD|COMMONHOLD|RESIDENTS ASSOCIATION|ESTATE MANAGEMENT",
                    na=False,
                    regex=True,
                )
            ),
        ),
        # Education Institution
        (
            "Education Institution",
            unclassified
            & (
                (div == 85)
                | name_upper.str.contains(
                    r"\bSCHOOL\b|ACADEMY TRUST|MULTI.ACADEMY|\bMAT\b|UNIVERSITY|STUDENTS.UNION|COLLEGE OF|NURSERY SCHOOL|PRE.SCHOOL|PLAYGROUP",
                    na=False,
                    regex=True,
                )
            ),
        ),
        # Sports Club
        (
            "Sports Club",
            unclassified
            & (
                (div == 93)
                | name_upper.str.contains(
                    r"FOOTBALL CLUB|CRICKET CLUB|RUGBY CLUB|TENNIS CLUB|GOLF CLUB|SWIMMING CLUB|BOWLING CLUB|ATHLETICS CLUB|HOCKEY CLUB|SAILING CLUB|ROWING CLUB|BOXING CLUB|GYMNASTICS|SPORTS CLUB|CYCLING CLUB",
                    na=False,
                    regex=True,
                )
            ),
        ),
        # Religious Organisation
        (
            "Religious Organisation",
            unclassified
            & (
                (sic == 94910)
                | name_upper.str.contains(
                    r"\bCHURCH\b|\bMOSQUE\b|\bSYNAGOGUE\b|\bTEMPLE\b|\bGURDWARA\b|\bCHAPEL\b|PARISH COUNCIL OF|PAROCHIAL CHURCH|DIOCESAN|METHODIST|BAPTIST|QUAKER|ISLAMIC CENTRE|CHRISTIAN FELLOWSHIP|GOSPEL HALL",
                    na=False,
                    regex=True,
                )
            ),
        ),
        # Arts Organisation
        (
            "Arts Organisation",
            unclassified
            & (
                div.isin({90, 91})
                | name_upper.str.contains(
                    r"\bTHEATRE\b|\bMUSEUM\b|\bGALLERY\b|ARTS CENTRE|ARTS COUNCIL|ORCHESTRA|CHOIR|CHORAL|DRAMA GROUP|FILM SOCIETY|MUSIC SOCIETY|LITERARY|HERITAGE TRUST|CONSERVATION TRUST",
                    na=False,
                    regex=True,
                )
            ),
        ),
        # Health Organisation
        ("Health Organisation", unclassified & div.isin({86, 87})),
        # Social Services Organisation
        ("Social Services Organisation", unclassified & (div == 88)),
        # Professional / Trade Body
        (
            "Professional / Trade Body",
            unclassified & sic.isin({94110, 94120, 94200}),
        ),
        # Membership Organisation
        ("Membership Organisation", unclassified & (div == 94)),
    ]

    for label, rule_mask in rules:
        # ``rules`` is constructed before this loop, so every stored mask was
        # evaluated against the initial unclassified set. Narrow it again here
        # to preserve the documented first-match-wins precedence. SIC columns
        # use pandas' nullable dtypes, so a missing five-digit SIC can produce
        # ``pd.NA`` here. Treat that as "this SIC condition did not match";
        # otherwise the unknown value poisons ``unclassified`` and prevents
        # later name-only rules from firing.
        mask = (unclassified & rule_mask).fillna(False)
        subtype = subtype.where(~mask, label)
        unclassified = unclassified & ~mask

    # Residual Other
    subtype = subtype.where(
        ~unclassified, "Other Company Limited By Guarantee"
    )

    spine["cso_subtype"] = subtype

    # Drop temporary SIC columns
    spine = spine.drop(columns=["primary_sic", "sic_div"])
    return spine


def prepare_primary_sic(sic_raw: pd.DataFrame) -> pd.DataFrame:
    """Choose the first SIC-2007 (five-digit) code for each uid.

    Four-digit legacy codes remain useful provenance in the published SIC
    lookup but must not be interpreted as SIC-2007 divisions.
    """
    candidates = sic_raw[["uid", "SIC"]].copy()
    candidates["primary_sic"] = pd.to_numeric(
        candidates["SIC"].astype(str).str.extract(
            r"^\s*(\d{5})(?!\d)", expand=False
        ),
        errors="coerce",
    )
    candidates = candidates[candidates["primary_sic"].notna()].copy()
    candidates["sic_div"] = (
        candidates["primary_sic"] // 1000
    ).astype("Int64")
    return candidates.drop_duplicates(subset="uid", keep="first")[
        ["uid", "primary_sic", "sic_div"]
    ]


def add_cso_type_to_spine(spine_path: str, sic_path: str, out_path: str = None) -> None:
    """Read the built spine and SIC codes file, append cso_type and
    cso_subtype, and write the result.

    If out_path is not given the spine file is rewritten in place, which
    is how the published release was produced.
    """
    if out_path is None:
        out_path = spine_path

    print("Loading spine...")
    spine = pd.read_csv(spine_path, low_memory=False)
    print(f"  {len(spine):,} rows, {len(spine.columns)} columns")

    print("Loading SIC codes...")
    sic_raw = pd.read_csv(
        sic_path,
        low_memory=False,
        dtype={"uid": str, "SIC": str},
        keep_default_na=False,
    )
    print(f"  {len(sic_raw):,} rows")

    # Extract the first five-digit SIC-2007 code per uid. Legacy four-digit
    # codes are retained in the lookup but are not valid inputs to these rules.
    sic_primary = prepare_primary_sic(sic_raw)

    # Normalise is_cic to boolean
    spine["is_cic"] = spine["is_cic"].astype(str).str.strip().str.lower() == "true"

    # Classify
    print("Classifying cso_type...")
    spine = add_cso_type(spine)

    print("Classifying cso_subtype...")
    spine = add_cso_subtype(spine, sic_primary)

    # Print distributions
    print("\ncso_type distribution:")
    print(spine["cso_type"].value_counts().sort_index())
    print(f"\ncso_subtype distribution:")
    print(spine["cso_subtype"].value_counts().sort_index())

    # Write back
    print(f"\nWriting {len(spine):,} rows to {out_path}...")
    spine.to_csv(out_path, index=False)
    print("Done.")
