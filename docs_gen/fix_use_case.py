import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9

def create_use_case_diagram():
    fig, ax = plt.subplots(figsize=(15, 12), dpi=300)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 12)
    ax.axis('off')

    # Title
    ax.text(7.5, 11.6, 'Raktsetu: UML Use Case Diagram', ha='center', va='center', 
            fontsize=16, fontweight='bold', color='#1A1214')
    ax.text(7.5, 11.25, 'Standard UML Model with Direct Associations, <<include>>, and <<extend>> Relationships', 
            ha='center', va='center', fontsize=10, fontstyle='italic', color='#555555')

    # System boundary
    rect = patches.FancyBboxPatch((3.8, 0.5), 7.4, 10.3, boxstyle="round,pad=0.2", 
                                  ec='#0F172A', fc='#F8FAFC', lw=2, ls='--')
    ax.add_patch(rect)
    ax.text(7.5, 10.5, 'System Boundary: Raktsetu National Blood Lakehouse', 
            ha='center', va='center', fontsize=11, fontweight='bold', color='#0F172A')

    # Clean non-overlapping Use Cases
    # (x, y, w, h, text, bg, border)
    ucs = [
        (6.0, 9.7, 3.4, 0.75, 'UC1: Search Inventory\n(District & Blood Group)', '#E0F2FE', '#0284C7'),
        (5.8, 8.6, 3.2, 0.75, 'UC2: Initiate Emergency\nTriage Mode', '#FEE2E2', '#DC2626'),
        (9.4, 8.6, 3.1, 0.75, 'UC3: Resolve Compatibility\n(WHO/NBTC Matrix)', '#FEF3C7', '#D97706'),
        (9.4, 7.5, 3.1, 0.75, 'UC4: Geolocation Proximity\n& Distance Filter', '#F1F5F9', '#475569'),
        (5.8, 7.5, 3.2, 0.75, 'UC5: Inspect 3-Pillar\nTrust Score Modal', '#DCFCE7', '#16A34A'),
        (6.0, 6.4, 3.4, 0.75, 'UC6: View Historical Trend\n& Depletion Flags', '#E0E7FF', '#4F46E5'),
        (6.0, 5.3, 3.4, 0.75, 'UC7: Calculate Donor\nEligibility (Private)', '#FCE7F3', '#DB2777'),
        (6.0, 4.2, 3.4, 0.75, 'UC8: Export Emergency Roster\n(Excel CSV / WhatsApp)', '#CFFAFE', '#0891B2'),
        (6.0, 3.1, 3.4, 0.75, 'UC9: Audit District Deficits\n& Shortage Radar', '#FFEDD5', '#EA580C'),
        (6.0, 2.0, 3.4, 0.75, 'UC10: Monitor Lakehouse Health\n& Freshness Metrics', '#CCFBF1', '#0D9488'),
        (6.0, 0.9, 3.4, 0.75, 'UC11: Update & Synchronize\nBed-Side Stock', '#EDE9FE', '#7C3AED')
    ]

    for x, y, w, h, label, bg, border in ucs:
        ellipse = patches.Ellipse((x, y), w, h, ec=border, fc=bg, lw=1.5)
        ax.add_patch(ellipse)
        ax.text(x, y, label, ha='center', va='center', fontsize=7.5, fontweight='bold', color='#1E293B')

    # Relationships between use cases
    # UC2 <<include>> UC3
    ax.annotate('', xy=(7.85, 8.6), xytext=(7.4, 8.6), arrowprops=dict(arrowstyle="->", ls="--", lw=1.3, color='#D97706'))
    ax.text(7.6, 8.85, '<<include>>', fontsize=7, color='#B45309', ha='center', fontweight='bold')

    # UC2 <<extend>> UC4
    ax.annotate('', xy=(7.4, 8.4), xytext=(8.0, 7.7), arrowprops=dict(arrowstyle="<-", ls="--", lw=1.3, color='#475569'))
    ax.text(7.9, 8.1, '<<extend>>', fontsize=7, color='#334155', ha='center', fontweight='bold')

    # Actor 1: Emergency Requester / Caregiver (Left)
    ax.plot(1.8, 6.8, 'o', ms=20, mfc='#E2E8F0', mec='#0F172A', mew=2)
    ax.plot([1.8, 1.8], [6.5, 5.2], color='#0F172A', lw=2.5)
    ax.plot([1.1, 2.5], [5.9, 5.9], color='#0F172A', lw=2.5)
    ax.plot([1.8, 1.2], [5.2, 4.0], color='#0F172A', lw=2.5)
    ax.plot([1.8, 2.4], [5.2, 4.0], color='#0F172A', lw=2.5)
    ax.text(1.8, 3.5, 'Emergency Requester\n/ General Citizen', ha='center', fontweight='bold', fontsize=9.5, color='#0F172A')

    # Lines from Requester to UCs
    for target_x, target_y in [(4.3, 9.7), (4.2, 8.6), (4.2, 7.5), (4.3, 6.4), (4.3, 5.3), (4.3, 4.2)]:
        ax.annotate('', xy=(target_x, target_y), xytext=(2.2, 5.9),
                    arrowprops=dict(arrowstyle="-", lw=1.2, color='#334155'))

    # Actor 2: Regional Health Officer (Right Top)
    ax.plot(13.2, 8.2, 'o', ms=18, mfc='#E2E8F0', mec='#0F172A', mew=2)
    ax.plot([13.2, 13.2], [7.9, 6.8], color='#0F172A', lw=2.5)
    ax.plot([12.6, 13.8], [7.4, 7.4], color='#0F172A', lw=2.5)
    ax.plot([13.2, 12.7], [6.8, 5.8], color='#0F172A', lw=2.5)
    ax.plot([13.2, 13.7], [6.8, 5.8], color='#0F172A', lw=2.5)
    ax.text(13.2, 5.3, 'Regional Health Officer\n/ Decision Maker', ha='center', fontweight='bold', fontsize=9, color='#0F172A')

    # Lines from Health Officer to UCs
    for target_x, target_y in [(7.7, 4.2), (7.7, 3.1), (7.7, 2.0)]:
        ax.annotate('', xy=(target_x, target_y), xytext=(12.5, 7.4),
                    arrowprops=dict(arrowstyle="-", lw=1.2, color='#0F172A'))

    # Actor 3: Blood Bank Officer (Right Bottom)
    ax.plot(13.2, 3.2, 'o', ms=18, mfc='#E2E8F0', mec='#0F172A', mew=2)
    ax.plot([13.2, 13.2], [2.9, 1.8], color='#0F172A', lw=2.5)
    ax.plot([12.6, 13.8], [2.4, 2.4], color='#0F172A', lw=2.5)
    ax.plot([13.2, 12.7], [1.8, 0.8], color='#0F172A', lw=2.5)
    ax.plot([13.2, 13.7], [1.8, 0.8], color='#0F172A', lw=2.5)
    ax.text(13.2, 0.4, 'Blood Bank Staff\n/ System Operator', ha='center', fontweight='bold', fontsize=9, color='#0F172A')

    # Lines from Operator to UCs
    for target_x, target_y in [(7.7, 2.0), (7.7, 0.9), (7.4, 7.5)]:
        ax.annotate('', xy=(target_x, target_y), xytext=(12.5, 2.4),
                    arrowprops=dict(arrowstyle="-", lw=1.2, color='#0F172A'))

    plt.tight_layout()
    plt.savefig('/home/radhey/Documents/project_idea/docs_gen/use_case_diagram.png', bbox_inches='tight', dpi=300)
    plt.close()
    print("Clean Use Case diagram regenerated successfully.")

if __name__ == '__main__':
    create_use_case_diagram()
