import pytest
import io

from .venn_diagrams import venn_diagram_of_CH_sources

@pytest.mark.xfail
def test_venn():
    for_csv_file = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,city,postcode,source
GB-COH-07391899,105 NORTH STREET MANAGEMENT COMPANY LIMITED,105 NORTH STREET MANAGEMENT COMPANY LIMITED,07391899,,"WHITTINGTON HALL, WHITTINGTON ROAD",WORCESTER,WR5 2ZX,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-03324062,THE LEGAL ADVICE CENTRE(UNIVERSITY HOUSE),THE LEGAL ADVICE CENTREUNIVERSITY HOUSE,03324062,,"104 ROMAN ROAD, BETHNAL GREEN",LONDON,E2 0RN,"[2014] CLG - [2023] PRI/LBG/NSC (Private, Limited by guarantee, no share capital, use of 'Limited' exemption)"
GB-COH-03324062,LEGAL ADVICE CENTRE (UNIVERSITY HOUSE),LEGAL ADVICE CENTRE UNIVERSITY HOUSE,03324062,,"104 ROMAN ROAD, BETHNAL GREEN",LONDON,E2 0RN,"[2014] CLG - [2023] PRI/LBG/NSC (Private, Limited by guarantee, no share capital, use of 'Limited' exemption)"
GB-COH-08715627,SAFBERRY LIMITED,SAFBERRY LIMITED,08715627,,,,SE1 7HR,[2014] CLG
GB-COH-SP1689RS,CENTRAL FIFE CO-OPERATIVE SOCIETY LIMITED,CENTRAL FIFE COOPERATIVE SOCIETY LIMITED,SP1689RS,,,,,[2014] Industrial and Provident Society - [2023] Registered Society
GB-COH-SC198586,ABERDEENSHIRE HOUSING PARTNERSHIP,ABERDEENSHIRE HOUSING PARTNERSHIP,SC198586,,,,AB51 5LX,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-SC198586,ABERDEENSHIRE HOUSING PARTNERSHIP,ABERDEENSHIRE HOUSING PARTNERSHIP,SC198586,,"22 ABERCROMBIE COURT, ARNHALL BUSINESS PARK, WESTHILL",ABERDEENSHIRE,AB32 6FE,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-SC198586,OSPREY HOUSING LIMITED,OSPREY HOUSING LIMITED,SC198586,,,,AB51 5LX,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-SC198586,OSPREY HOUSING LIMITED,OSPREY HOUSING LIMITED,SC198586,,"22 ABERCROMBIE COURT, ARNHALL BUSINESS PARK, WESTHILL",ABERDEENSHIRE,AB32 6FE,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-06060352,CHAGSTOCK LIMITED,CHAGSTOCK LIMITED,06060352,,,,EX20 1AS,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"GB-COH-08894088,CATALYST COUNSELLING CIC,CATALYST COUNSELLING CIC,08894088,,,,NR32 1NL,[2014] Community Interest Company - [2023] Community Interest Company - [gap] community-interest-company
GB-COH-08894088,CATALYST COUNSELLING CIC,CATALYST COUNSELLING CIC,08894088,,"44 ALEXANDRA ROAD, ",LOWESTOFT,NR32 1PJ,[2014] Community Interest Company - [2023] Community Interest Company - [gap] community-interest-company
GB-COH-03817479,THE BANKS (CHISWICK HIGH ROAD) MANAGEMENT COMPANY LIMITED,THE BANKS CHISWICK HIGH ROAD MANAGEMENT COMPANY LIMITED,03817479,,"RMG HOUSE, ESSEX ROAD",HODDESDON,EN11 0DR,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-06656031,THE HOLLIES MANAGEMENT (BRISTOL) COMPANY LIMITED,THE HOLLIES MANAGEMENT BRISTOL COMPANY LIMITED,06656031,,,,SY2 6LG,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-06656031,THE HOLLIES MANAGEMENT (BRISTOL) COMPANY LIMITED,THE HOLLIES MANAGEMENT BRISTOL COMPANY LIMITED,06656031,,"THE CLOCKHOUSE BATH HILL, KEYNSHAM",BRISTOL,BS31 1HL,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-02800737,NOTLEY LODGE MANAGEMENT COMPANY LIMITED,NOTLEY LODGE MANAGEMENT COMPANY LIMITED,02800737,,"SUNNYFIELDS COTTAGE, SUNNYFIELDS ROAD",BRAINTREE,CM7 5PG,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-08806350,JALEGUL LIMITED,JALEGUL LIMITED,08806350,,,,SE1 7HR,[2014] CLG
GB-COH-08860534,GRINDON LIMITED,GRINDON LIMITED,08860534,,,,SE1 7HR,[gap]
GB-COH-03240360,WELLINGBOROUGH AFRO-CARIBBEAN ASSOCIATION,WELLINGBOROUGH AFROCARIBBEAN ASSOCIATION,03240360,,27-29 ROCK STREET,WELLINGBOROUGH,NN8 4LW,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"
GB-COH-03240360,WELLINGBOROUGH AFRICAN CARIBBEAN ASSOCIATION LTD,WELLINGBOROUGH AFRICAN CARIBBEAN ASSOCIATION LTD,03240360,,27-29 ROCK STREET,WELLINGBOROUGH,NN8 4LW,"[2014] CLG - [2023] PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)"'''

    
    f1 = io.StringIO(for_csv_file)
    f2 = io.StringIO('out.tmp')
    expected={'A': 1, 'B': 0, 'AB': 0, 'C': 0, 'AC': 5, 'BC': 0, 'ABC': 0}
    assert venn_diagram_of_CH_sources(f1,f2) == expected