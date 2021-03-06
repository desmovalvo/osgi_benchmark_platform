//
// C++ Implementation: PropertyVolume
//
// Author: Michael Schmidt, Christoph Pinkel <>, (C) 2007-2008
// Copyright: See COPYING file that comes with this distribution
//
#include "propertyvolume.h"

PropertyVolume::PropertyVolume(RDFTriple *main_triple,
    unsigned _doctype, unsigned _docid, unsigned _year) :
    Property(PROPERTY_VOLUME, main_triple), doctype(_doctype),
    docid(_docid), year(_year)
{
}


PropertyVolume::~PropertyVolume()
{
}


/*!
    \fn PropertyVolume:: calc()
 */
bool PropertyVolume:: calc()
{
VolumeMgr * vm = VolumeMgr::getInstance();

    RDFObject *o1 = new RDFObject(RDFObject::URIObj,
        mainTriple()->getSubjectPtr()->getString());
    RDFObject *o2 = new RDFObject("swrc", "volume");
    RDFObject *o3 = 0L;
    
    unsigned vnum = 0;
    
    switch(doctype)
    {
        case DOCTYPE_JOURNAL:
            vnum = vm->getVol(0, docid, year);
            break;
            
        case DOCTYPE_PROCEEDINGS:
            vnum = vm->getVol(1, docid, year);
            break;
            
        case DOCTYPE_BOOK:
            vnum = vm->getVol(2, docid, year);
            break;

        default:
            break;
    }
    
    if(vnum)
    {
    char *vol = StringTools::numStr("", vnum);
        o3 = new RDFObject(vol,1);
        delete[] vol;
    }
    else
        o3 = new RDFObject("1",1);
    
    setObjs(o1, o2, o3);

    return true;
}
